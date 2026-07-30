"""Black-box tests for BacktestResult: hand-built runs in, metrics out, asserted
against first-principles expectations (not the implementation). Meant to catch bugs
where the code disagrees with what a metric is *supposed* to be."""

import numpy as np
import pytest

from backtesting.lighter import Strategy, Backtester
from backtesting.lighter.persistence import save_run
from backtesting.lighter.instruments.visualize import BacktestResult


def _result(tmp_path, *, pnl, quotes, fills):
    """Persist a hand-built run (3 array groups → 14 columns) and load it back."""
    save_run({**pnl, **quotes, **fills}, str(tmp_path / "run"))
    return BacktestResult(str(tmp_path / "run"))


def test_exact_decomposition_known_answer(tmp_path):
    # Round trip: buy 2 @99 when mid=100, price rises, sell 2 @106 when mid=105.
    #   spread_capture = +1·(100−99)·2 + (−1)·(105−106)·2 = 2 + 2 = 4
    #   inventory_mtm  = held +2 while mid went 100→105 (Δ5) = 2·5   = 10
    #   total (cash)   = spread_capture + inventory_mtm            = 14
    #   turnover       = 99·2 + 106·2                              = 410
    r = _result(
        tmp_path,
        pnl=dict(pnl_t=np.array([0, 10, 20, 30]) * 1_000_000,
                 pnl_v=np.array([0.0, 2.0, 12.0, 14.0]),
                 inv_v=np.array([0.0, 2.0, 2.0, 0.0])),
        quotes=dict(qt_t=np.array([0, 10, 20, 30]) * 1_000_000,
                    qt_mid=np.array([100.0, 100.0, 105.0, 105.0]),
                    qt_bid=np.array([99.9, 99.0, 104.9, 104.9]),
                    qt_ask=np.array([100.1, 100.1, 105.1, 105.1])),
        fills=dict(fill_t=np.array([10, 30, 30]) * 1_000_000,
                   fill_side=np.array([0, 1, 2], np.int32),        # bid, ask, markout
                   fill_price=np.array([99.0, 106.0, 105.0]),
                   fill_size=np.array([2.0, 2.0, 0.0]),
                   fill_inv=np.array([2.0, 0.0, 0.0]),
                   fill_mid=np.array([100.0, 105.0, 105.0]),
                   fill_fee=np.array([0.0, 0.0, 0.0])),
    )
    m = r.summary()
    assert m["total_pnl"] == pytest.approx(14.0)
    assert m["spread_capture_usd"] == pytest.approx(4.0)
    assert m["inv_mtm_usd"] == pytest.approx(10.0)
    assert m["identity_gap_usd"] == pytest.approx(0.0, abs=1e-9)
    assert m["fees_usd"] == pytest.approx(0.0)
    assert m["turnover_usd"] == pytest.approx(410.0)
    assert m["capture_yield_bps"] == pytest.approx(4.0 / 410.0 * 1e4)
    assert m["n_fills"] == 2
    assert m["n_bid_fills"] == 1 and m["n_ask_fills"] == 1
    assert m["fill_imbalance"] == pytest.approx(0.0)
    assert m["spread_capture_pct"] == pytest.approx(4.0 / 14.0 * 100)
    assert m["inv_mtm_pct"] == pytest.approx(10.0 / 14.0 * 100)


def test_fees_enter_decomposition_and_net_pnl(tmp_path):
    # same round trip, but 0.5 bps of notional is charged per fill → PnL is net of fees,
    # while spread_capture / inventory_mtm stay gross and the identity still closes:
    #   total_net = spread_capture + inventory_mtm − fees
    fee_bid, fee_ask = 99.0 * 2 * 0.5e-4, 106.0 * 2 * 0.5e-4      # 0.0099, 0.0106
    fees = fee_bid + fee_ask
    total_net = 4.0 + 10.0 - fees
    r = _result(
        tmp_path,
        pnl=dict(pnl_t=np.array([0, 10, 20, 30]) * 1_000_000,
                 pnl_v=np.array([0.0, 2.0 - fee_bid, 12.0 - fee_bid, total_net]),
                 inv_v=np.array([0.0, 2.0, 2.0, 0.0])),
        quotes=dict(qt_t=np.array([0, 10, 20, 30]) * 1_000_000,
                    qt_mid=np.array([100.0, 100.0, 105.0, 105.0]),
                    qt_bid=np.array([99.9, 99.0, 104.9, 104.9]),
                    qt_ask=np.array([100.1, 100.1, 105.1, 105.1])),
        fills=dict(fill_t=np.array([10, 30, 30]) * 1_000_000,
                   fill_side=np.array([0, 1, 2], np.int32),
                   fill_price=np.array([99.0, 106.0, 105.0]),
                   fill_size=np.array([2.0, 2.0, 0.0]),
                   fill_inv=np.array([2.0, 0.0, 0.0]),
                   fill_mid=np.array([100.0, 105.0, 105.0]),
                   fill_fee=np.array([fee_bid, fee_ask, 0.0])),
    )
    m = r.summary()
    assert m["fees_usd"] == pytest.approx(fees)
    assert m["total_pnl"] == pytest.approx(total_net)
    assert m["spread_capture_usd"] == pytest.approx(4.0)         # gross, fee-independent
    assert m["inv_mtm_usd"] == pytest.approx(10.0)
    assert m["identity_gap_usd"] == pytest.approx(0.0, abs=1e-9)


# ── invariant tests: properties that must hold for ANY valid engine run ──

class _Quoter(Strategy):
    def on_lob(self, ob, inventory):
        self.gateway.create_order(+1.0, ob.best_bid, ttl_s=0.3)
        self.gateway.create_order(-1.0, ob.best_ask, ttl_s=0.3)


class _Feed:
    def __init__(self, d): self._d = d
    def arrays(self): return self._d


def _random_run(tmp_path, seed, fee_bps):
    """A real engine run on a random synthetic feed → a persisted, valid BacktestResult."""
    rng = np.random.default_rng(seed)
    n = 300
    lob_ts = (np.arange(n) * 100_000 + 1).astype(np.int64)            # 100 ms apart → ~30 s span
    mid = 100.0 + np.cumsum(rng.normal(0.0, 0.05, n))
    bid0, ask0 = (mid - 0.1).astype(np.float32), (mid + 0.1).astype(np.float32)
    z, three = np.zeros(n, np.float32), np.full(n, 3.0, np.float32)
    feed = _Feed(dict(
        lob_ts=lob_ts,
        bid_px=np.column_stack([bid0, z]), bid_sz=np.column_stack([three, z]),      # deeper bid = 0 sentinel
        ask_px=np.column_stack([ask0, np.full(n, 1e18, np.float32)]),               # deeper ask sentinel
        ask_sz=np.column_stack([three, z]),
        trade_ts=None, trade_is_sell=None, trade_price=None, trade_size=None,
    ))
    m = int(rng.integers(20, 60))
    # keep trades in the interior (not the first/last grid second) so every fill lands
    # inside the PnL-derived grid — then the fill-aware grid MtM is exactly the checkpoint
    # MtM. Boundary fills are covered separately by the no-crash regression test below.
    tt = np.sort(rng.integers(1_500_000, n * 100_000 - 1_500_000, m)).astype(np.int64)
    tsell = rng.integers(0, 2, m).astype(np.uint8)
    mid_at = np.interp(tt, lob_ts, mid)
    tpx = np.where(tsell == 1, mid_at - 0.15, mid_at + 0.15)          # cross our quotes → fills
    d = feed._d
    d.update(trade_ts=tt, trade_is_sell=tsell, trade_price=tpx, trade_size=rng.uniform(1.0, 5.0, m))
    prefix = str(tmp_path / f"run{seed}")
    Backtester(latency_us=0, log_interval_sec=1.0, quote_log_stride=1,
               fee_bps=fee_bps).run(_Quoter(), feed, output_path=prefix)
    return BacktestResult(prefix)


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("fee_bps", [0.0, 0.5])
def test_accounting_identity_holds_on_random_runs(tmp_path, seed, fee_bps):
    m = _random_run(tmp_path, seed, fee_bps).summary()
    # total cash (engine) must equal the analysis decomposition, to ~machine precision
    assert abs(m["identity_gap_usd"]) < 1e-6
    # fill-aware grid MtM must equal the exact checkpoint MtM
    assert abs(m["inv_mtm_grid_error_usd"]) < 1e-6
    # fees are exactly the charged rate on the traded notional
    assert m["fees_usd"] == pytest.approx(fee_bps * 1e-4 * m["turnover_usd"], abs=1e-9)


def test_fill_before_first_pnl_snapshot_does_not_crash(tmp_path):
    """Regression: a trade in the first second (before the first PnL snapshot) lands in a
    grid second that does not exist in the PnL-derived grid. It once crashed _grid_mtm with
    a KeyError; summary() must now handle it, and the exact accounting still closes."""
    n = 30
    lob_ts = (np.arange(n) * 100_000 + 1).astype(np.int64)               # ~3 s span
    z, three = np.zeros(n, np.float32), np.full(n, 3.0, np.float32)
    feed = _Feed(dict(
        lob_ts=lob_ts,
        bid_px=np.column_stack([np.full(n, 99.9, np.float32), z]), bid_sz=np.column_stack([three, z]),
        ask_px=np.column_stack([np.full(n, 100.1, np.float32), np.full(n, 1e18, np.float32)]),
        ask_sz=np.column_stack([three, z]),
        trade_ts=np.array([50_000], np.int64),                          # 50 ms: before the ~1 s first snapshot
        trade_is_sell=np.array([1], np.uint8),                          # sell hits our resting bid
        trade_price=np.array([99.8]), trade_size=np.array([2.0]),
    ))
    prefix = str(tmp_path / "early")
    Backtester(latency_us=0, log_interval_sec=1.0, quote_log_stride=1).run(_Quoter(), feed, output_path=prefix)
    m = BacktestResult(prefix).summary()                                # must not raise
    assert abs(m["identity_gap_usd"]) < 1e-6


# ── worst_unrealized: deepest inventory·(mid − avg_entry), VWAP entry rules ──
# avg_entry: add/open → VWAP, partial reduce → keep, flip → reset to the flip fill price.

def _scenario(tmp_path, *, secs, inv, mid, pnl, fills, bid=None, ask=None):
    """Build a run on a shared time grid and return summary(). fills entries are
    (t_s, side, price, size, inv_after, mid_at_fill). bid/ask default to mid ∓ 0.1
    but can be passed (with NaN) to control quote presence."""
    t = np.array(secs, np.int64) * 1_000_000
    mid = np.array(mid, float)
    save_run(dict(
        pnl_t=t, pnl_v=np.array(pnl, float), inv_v=np.array(inv, float),
        qt_t=t, qt_mid=mid,
        qt_bid=np.array(bid, float) if bid is not None else mid - 0.1,
        qt_ask=np.array(ask, float) if ask is not None else mid + 0.1,
        fill_t=np.array([f[0] for f in fills], np.int64) * 1_000_000,
        fill_side=np.array([f[1] for f in fills], np.int32),
        fill_price=np.array([f[2] for f in fills], float),
        fill_size=np.array([f[3] for f in fills], float),
        fill_inv=np.array([f[4] for f in fills], float),
        fill_mid=np.array([f[5] for f in fills], float),
        fill_fee=np.zeros(len(fills)),
    ), str(tmp_path / "sc"))
    return BacktestResult(str(tmp_path / "sc")).summary()


def _wu(tmp_path, **kw):
    return _scenario(tmp_path, **kw)["worst_unrealized_usd"]


def test_worst_unrealized_long_dip(tmp_path):
    # long +1 @entry 100; mid dips to 95 → unrealized = 1·(95−100) = −5
    wu = _wu(tmp_path,
             secs=[0, 2, 5, 8, 10], inv=[0, 1, 1, 1, 0],
             mid=[100, 100, 95, 102, 102], pnl=[0, 0, -5, 2, 2],
             fills=[(2, 0, 100, 1, 1, 100), (10, 1, 102, 1, 0, 102), (10, 2, 102, 0, 0, 102)])
    assert wu == pytest.approx(-5.0)


def test_worst_unrealized_add_updates_vwap(tmp_path):
    # buy 1 @100 then add 1 @120 → VWAP entry 110 for +2; mid → 100 → 2·(100−110) = −20
    wu = _wu(tmp_path,
             secs=[0, 2, 4, 8, 10], inv=[0, 1, 2, 2, 0],
             mid=[100, 100, 120, 100, 100], pnl=[0, 0, 20, -20, -20],
             fills=[(2, 0, 100, 1, 1, 100), (4, 0, 120, 1, 2, 120),
                    (10, 1, 100, 2, 0, 100), (10, 2, 100, 0, 0, 100)])
    assert wu == pytest.approx(-20.0)


def test_worst_unrealized_partial_reduce_keeps_vwap(tmp_path):
    # +2 @100, sell 1 @105 reduces to +1 with entry KEPT at 100; mid → 90 → 1·(90−100) = −10
    wu = _wu(tmp_path,
             secs=[0, 2, 5, 8, 10], inv=[0, 2, 1, 1, 0],
             mid=[100, 100, 105, 90, 90], pnl=[0, 0, 10, -5, -5],
             fills=[(2, 0, 100, 2, 2, 100), (5, 1, 105, 1, 1, 105),
                    (10, 1, 90, 1, 0, 90), (10, 2, 90, 0, 0, 90)])
    assert wu == pytest.approx(-10.0)


def test_worst_unrealized_flip_resets_entry(tmp_path):
    # +2 @100, sell 3 @110 flips to −1 with entry reset to 110; mid → 120 → −1·(120−110) = −10
    # (a bug that kept the old VWAP 100 would give −1·(120−100) = −20)
    wu = _wu(tmp_path,
             secs=[0, 2, 5, 8, 10], inv=[0, 2, -1, -1, 0],
             mid=[100, 100, 110, 120, 120], pnl=[0, 0, 20, 10, 10],
             fills=[(2, 0, 100, 2, 2, 100), (5, 1, 110, 3, -1, 110),
                    (10, 0, 120, 1, 0, 120), (10, 2, 120, 0, 0, 120)])
    assert wu == pytest.approx(-10.0)


# ── markout / net_edge: captured half-spread + forward-mid move at markout_s (30 s) ──

def test_markout_and_net_edge_known_answer(tmp_path):
    # one bid fill @99.5 when mid=100 → captured = +1·(100−99.5)/100·1e4 = 50 bps.
    # grid mid 30 s later = 101 → markout = +1·(101−100)/100·1e4 = 100 bps.
    # net_edge = captured + markout = 150 bps.
    m = _scenario(tmp_path,
                  secs=[0, 30, 60], inv=[1, 1, 0], mid=[100, 101, 101], pnl=[0.5, 1.5, 1.5],
                  fills=[(0, 0, 99.5, 1, 1, 100), (60, 2, 101, -1, 0, 101)])
    assert m["markout_30s_bps"] == pytest.approx(100.0)
    assert m["net_edge_per_fill_bps"] == pytest.approx(150.0)


# ── max_drawdown: deepest peak-to-trough of the PnL curve ──

def test_max_drawdown_known_answer(tmp_path):
    # PnL 0 → 10 → 3 → 8; running max [0,10,10,10]; drawdown min = 3 − 10 = −7
    m = _scenario(tmp_path,
                  secs=[0, 1, 2, 3], inv=[0, 0, 0, 0], mid=[100, 100, 100, 100],
                  pnl=[0, 10, 3, 8], fills=[(3, 2, 100, 0, 0, 100)])
    assert m["max_drawdown"] == pytest.approx(-7.0)


# ── capture_share_of_variance = 1 − corr(ΔPnL, inventory·Δmid)² ──

def test_capture_share_pure_drift_is_zero(tmp_path):
    # PnL is entirely inventory MtM (fills exactly at mid → zero spread captured), so the
    # per-second ΔPnL series equals inventory·Δmid → corr = 1 → capture_share = 1 − 1 = 0.
    # A 1-second ΔPnL vs d_mtm misalignment (the historical bug) would push this well above 0.
    m = _scenario(tmp_path,
                  secs=[0, 1, 2, 3, 4, 5], inv=[1, 1, 1, 1, 1, 0],
                  mid=[100, 101, 99, 102, 98, 100], pnl=[0, 1, -1, 2, -2, 0],
                  fills=[(0, 0, 100, 1, 1, 100), (5, 1, 100, 1, 0, 100), (5, 2, 100, 0, 0, 100)])
    assert m["capture_share_of_variance"] == pytest.approx(0.0, abs=0.05)


# ── inventory shape (time-weighted over the grid) ──

def test_inventory_stats_known_answer(tmp_path):
    # grid inventory = [0, 2, -4, 0]
    m = _scenario(tmp_path, secs=[0, 1, 2, 3], inv=[0, 2, -4, 0], mid=[100, 100, 100, 100],
                  pnl=[0, 0, 0, 0], fills=[(3, 2, 100, 0, 0, 100)])
    assert m["avg_inventory"] == pytest.approx(-0.5)       # mean([0, 2, -4, 0])
    assert m["mean_abs_inventory"] == pytest.approx(1.5)   # mean([0, 2, 4, 0])
    assert m["max_abs_inventory"] == pytest.approx(4.0)


# ── two_sided_uptime: fraction of grid seconds with both a live bid and ask ──

def test_two_sided_uptime_known_answer(tmp_path):
    # ask quoted only at seconds 0,1 (NaN after) → both-sided at 2/4 seconds = 50%
    m = _scenario(tmp_path, secs=[0, 1, 2, 3], inv=[0, 0, 0, 0], mid=[100, 100, 100, 100],
                  pnl=[0, 0, 0, 0], fills=[(3, 2, 100, 0, 0, 100)],
                  bid=[99.9, 99.9, 99.9, 99.9], ask=[100.1, 100.1, np.nan, np.nan])
    assert m["two_sided_uptime_pct"] == pytest.approx(50.0)


# ── n_jumps: grid seconds whose |Δmid/mid| exceeds jump_bps (default 20) ──

def test_n_jumps_known_answer(tmp_path):
    # mid steps 100→101 once → one 100 bps second (> 20); the rest are 0 bps
    m = _scenario(tmp_path, secs=[0, 1, 2, 3], inv=[0, 0, 0, 0], mid=[100, 100, 101, 101],
                  pnl=[0, 0, 0, 0], fills=[(3, 2, 100, 0, 0, 100)])
    assert m["n_jumps"] == 1


# ── sharpe: zero when per-second ΔPnL has no dispersion (std == 0 guard) ──

def test_sharpe_zero_on_constant_increments(tmp_path):
    m = _scenario(tmp_path, secs=[0, 1, 2, 3], inv=[0, 0, 0, 0], mid=[100, 100, 100, 100],
                  pnl=[0, 1, 2, 3], fills=[(3, 2, 100, 0, 0, 100)])   # ΔPnL = [1,1,1], std 0
    assert m["sharpe_annualized"] == 0.0


# ── smoke: summary_df builds the table, plots build figures (no metric asserts) ──

def test_summary_df_and_plots_smoke(tmp_path):
    import plotly.graph_objects as go
    r = _random_run(tmp_path, 0, 0.5)
    df = r.summary_df()
    assert list(df.index.names) == ["group", "metric"]
    assert ("PnL", "total_pnl ($)") in df.index
    assert ("PnL", "fees ($)") in df.index
    assert "value" in df.columns
    assert isinstance(r.plot(), go.Figure)
    assert isinstance(r.plot_price(), go.Figure)
