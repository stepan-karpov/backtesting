"""Black-box tests for the isolatable parts of LighterFeed: depth validation, the
float32 precision guard, and the array/repr handoff. The streaming parquet/zst load
goes through the venue readers (tools.readers.lighter) — out of scope here — so it is
exercised only end-to-end elsewhere, not unit-tested with fabricated venue files."""

import numpy as np
import pytest

from backtesting.lighter import LighterFeed


def test_depth_out_of_range_raises():
    # depth is checked before any file is touched, so bogus paths are fine here
    with pytest.raises(ValueError):
        LighterFeed("lob", "trades", depth=0)
    with pytest.raises(ValueError):
        LighterFeed("lob", "trades", depth=31)      # > MAX_LOB_LEVELS (30)


# ── float32 precision guard: raise if float32's ULP at the top price blurs the tick ──

def _check(max_price, top_uniques):
    f = LighterFeed.__new__(LighterFeed)            # bypass __init__ (no data load)
    f.depth = 15
    f._check_float32_precision(max_price, top_uniques)


def test_float32_guard_passes_low_price():
    # DOGE-like: price ~0.1, tick 1e-4 → ULP ~1.2e-8 ≪ 0.05·tick = 5e-6 → fine
    _check(0.1, [np.array([0.1000, 0.1001, 0.1002])])


def test_float32_guard_raises_on_high_price():
    # BTC-like: price ~1e5, tick 0.1 → ULP ~0.012 ≥ 0.05·tick = 0.005 → too coarse
    with pytest.raises(ValueError):
        _check(100_000.0, [np.array([100_000.0, 100_000.1, 100_000.2])])


def test_float32_guard_noop_without_a_tick():
    _check(100.0, [])                               # nothing collected → no check
    _check(100.0, [np.array([100.0])])              # a single price → no tick to infer


# ── arrays() / __repr__ handoff ──

def test_arrays_and_repr():
    f = LighterFeed.__new__(LighterFeed)
    f.depth, n = 2, 3
    f.lob_ts = np.arange(n, dtype=np.int64)
    f.bid_px = f.bid_sz = f.ask_px = f.ask_sz = np.zeros((n, 2), np.float32)
    f.trade_ts = np.array([0], np.int64)
    f.trade_is_sell = np.array([1], np.uint8)
    f.trade_price = np.array([100.0])
    f.trade_size = np.array([1.0])
    a = f.arrays()
    assert set(a) == {"lob_ts", "bid_px", "bid_sz", "ask_px", "ask_sz",
                      "trade_ts", "trade_is_sell", "trade_price", "trade_size"}
    assert a["lob_ts"] is f.lob_ts                  # handed over, not copied
    assert "LighterFeed(depth=2" in repr(f)
