"""End-to-end tests of the Python↔engine seam: orders issued through the real
`gateway.create_order` are decoded in bindings.cpp (size sign → side, `ttl_s`
seconds → µs, reduce_only) and matched by the engine over a whole run. The C++ suite
covers the same execution mechanics with C++-injected Orders; here the binding decode
and the C++→Python exception propagation are what's under test. Ported from
BacktestingChecks.ipynb (checks H/I/J/K) — the only notebook checks whose value lived
in the Python API path rather than in the pure-engine unit tests.

The feed is a fabricated in-memory ArrayFeed (any object exposing .arrays() is a valid
feed); the venue readers are not involved, so this stays inside the engine's scope."""

import numpy as np
import pytest

from backtesting.lighter import Strategy, Backtester
from backtesting.lighter.instruments.visualize import BacktestResult

FAR_ASK = 1e18


class _ArrayFeed:
    """Minimal in-memory feed — the same .arrays() contract as LighterFeed."""
    def __init__(self, arrays):
        self._arrays = arrays

    def arrays(self):
        return self._arrays


def _feed(snaps, trades, depth=2):
    """Tiny feed from top-of-book rows: snaps=(ts, bid_px, bid_sz, ask_px, ask_sz),
    trades=(ts, is_sell, price, size). depth=2 pads an out-of-reach floor/ceiling so a
    trade larger than the top level stops by price instead of tripping the punch-through
    escalation; pass depth=1 to exercise that escalation on purpose (check K)."""
    n = len(snaps)
    bid_px = np.zeros((n, depth)); bid_sz = np.zeros((n, depth))
    ask_px = np.full((n, depth), FAR_ASK); ask_sz = np.zeros((n, depth))
    for i, (_, bp, bs, ap, asz) in enumerate(snaps):
        bid_px[i, 0], bid_sz[i, 0] = bp, bs
        ask_px[i, 0], ask_sz[i, 0] = ap, asz
    return _ArrayFeed(dict(
        lob_ts=np.array([s[0] for s in snaps], np.int64),
        bid_px=bid_px, bid_sz=bid_sz, ask_px=ask_px, ask_sz=ask_sz,
        trade_ts=np.array([t[0] for t in trades], np.int64),
        trade_is_sell=np.array([t[1] for t in trades], np.uint8),
        trade_price=np.array([t[2] for t in trades], np.float64),
        trade_size=np.array([t[3] for t in trades], np.float64),
    ))


class _CreateOnce(Strategy):
    """Issue a fixed order set on the first LOB event only, via the gateway API.
    orders: (size, price, ttl_s, reduce_only) — size's sign carries the side."""
    def __init__(self, orders):
        super().__init__()
        self._orders, self._fired = orders, False

    def on_lob(self, ob, inventory):
        if self._fired:
            return
        self._fired = True
        for size, price, ttl_s, ro in self._orders:
            self.gateway.create_order(size, price, ttl_s=ttl_s, reduce_only=ro)


def _fills(tmp_path, orders, feed, latency_us):
    prefix = str(tmp_path / "seam")
    Backtester(latency_us=latency_us, log_interval_sec=10.0).run(
        _CreateOnce(orders), feed=feed, output_path=prefix)
    return BacktestResult(prefix).fills


def _n(fills, side=None):
    col = fills["side"]
    return int((col != "markout").sum() if side is None else (col == side).sum())


# ── H. a bid created via create_order fills only once it has landed (latency gate) ──
def test_created_bid_respects_latency(tmp_path):
    # GTC bid created on the first snapshot; sell@100 (queue 10) fills 5 of our 5.
    feed = _feed([(0, 100.0, 10.0, 101.0, 10.0)], [(100, 1, 100.0, 100.0)])
    landed = _fills(tmp_path, [(+5.0, 100.0, 0.0, False)], feed, latency_us=0)
    late = _fills(tmp_path, [(+5.0, 100.0, 0.0, False)], feed, latency_us=200)
    assert _n(landed) == 1
    assert abs(landed[landed["side"] == "bid"]["size"].iloc[0] - 5.0) < 1e-9   # sign → bid
    assert _n(late) == 0                                                        # lands after trade


# ── I. ttl_s is decoded seconds → µs: the order is reaped at landing + ttl ──
def test_ttl_seconds_are_converted_to_micros(tmp_path):
    snaps = [(0, 100.0, 0.0, 101.0, 0.0)]                 # queue 0 → any sell fills while alive
    live = _fills(tmp_path, [(+5.0, 100.0, 1e-3, False)], _feed(snaps, [(500, 1, 100.0, 100.0)]), 0)
    dead = _fills(tmp_path, [(+5.0, 100.0, 1e-3, False)], _feed(snaps, [(2000, 1, 100.0, 100.0)]), 0)
    assert _n(live) == 1                                  # 500 µs < 1000 µs ttl → still resting
    assert _n(dead) == 0                                  # 2000 µs > 1000 µs ttl → reaped


# ── J. reduce_only fills only when it shrinks |inventory| ──
def test_reduce_only_needs_offsetting_inventory(tmp_path):
    # flat inventory → reduce-only ask has capacity 0 → no fill even though a buy reaches it
    flat = _feed([(0, 100.0, 0.0, 101.0, 0.0)], [(100, 0, 101.0, 100.0)])
    j1 = _fills(tmp_path, [(-5.0, 101.0, 0.0, True)], flat, 0)
    assert _n(j1, "ask") == 0
    # sell@100 fills our bid first (inventory +5), then buy@101 lets the reduce-only ask fill
    long = _feed([(0, 100.0, 0.0, 101.0, 0.0)],
                 [(100, 1, 100.0, 100.0), (200, 0, 101.0, 100.0)])
    j2 = _fills(tmp_path, [(+5.0, 100.0, 0.0, False), (-5.0, 101.0, 0.0, True)], long, 0)
    assert _n(j2, "ask") == 1


# ── K. a trade punching through all loaded levels escalates as a RuntimeError that
#    propagates out of run_arrays (C++ throw → pybind → Python) ──
def test_punch_through_all_levels_raises(tmp_path):
    # depth=1 book (bid@100 size 10); a sell of 100 exhausts the only level, no floor to stop it
    feed = _feed([(0, 100.0, 10.0, 101.0, 10.0)], [(100, 1, 100.0, 100.0)], depth=1)
    with pytest.raises(RuntimeError, match="punched through"):
        _fills(tmp_path, [(+5.0, 100.0, 0.0, False)], feed, 0)


# ── ob.bid_volume(n) / ask_volume(n): C++-side sum of the top-n resting amounts,
#    clamped to depth, n <= 0 → 0. The allocation-free replacement for summing
#    ob.bids[i][1] in Python (which rebuilds the whole depth list per access). ──
def test_bid_ask_volume_sum_top_n_and_clamp(tmp_path):
    depth = 4
    one = lambda vals: np.array([vals], np.float32)          # one snapshot, `depth` levels
    arrays = dict(
        lob_ts=np.array([0], np.int64),
        bid_px=one([100., 99., 98., 97.]), bid_sz=one([1., 2., 3., 4.]),
        ask_px=one([101., 102., 103., 104.]), ask_sz=one([10., 20., 30., 40.]),
        trade_ts=np.array([0], np.int64), trade_is_sell=np.array([0], np.uint8),
        trade_price=np.array([100.0]), trade_size=np.array([0.0]),
    )
    seen = {}

    class _Capture(Strategy):
        def on_lob(self, ob, inventory):
            seen["b1"], seen["b3"] = ob.bid_volume(1), ob.bid_volume(3)
            seen["b_clamp"], seen["b0"] = ob.bid_volume(100), ob.bid_volume(0)
            seen["a2"], seen["a_default"] = ob.ask_volume(2), ob.ask_volume()

    Backtester(latency_us=0, log_interval_sec=10.0).run(
        _Capture(), feed=_ArrayFeed(arrays), output_path=str(tmp_path / "vol"))

    assert seen["b1"] == 1.0                 # top level only
    assert seen["b3"] == 6.0                 # 1 + 2 + 3
    assert seen["b_clamp"] == 10.0           # n > depth → clamped to all four: 1+2+3+4
    assert seen["b0"] == 0.0                 # n <= 0 sums nothing
    assert seen["a2"] == 30.0                # 10 + 20
    assert seen["a_default"] == 10.0         # default n=1 → top level
