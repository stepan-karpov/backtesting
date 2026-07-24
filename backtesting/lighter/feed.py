from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ._engine import MAX_LOB_LEVELS

# ─────────────────────────────────────────────────────────────────────────────
# LighterFeed — Lighter market data → normalised numpy arrays for the engine.
#
# This is the ONLY venue-aware piece of the framework: it knows Lighter's
# parquet/zst layout and column names. Everything downstream (the C++ engine,
# Backtester, Strategy) sees only the normalised columns below. A BinanceFeed /
# MexcFeed with the same `.arrays()` output would drop in without engine changes.
#
# Only `depth` book levels are read (parquet column projection) — a strategy that
# indexes ob.bids/ob.asks beyond `depth` gets an IndexError, so the cap is loud.
#
# Normalised contract (matches run_arrays in bindings.cpp):
#   lob_ts        int64  [n_lob]           — exchange time (sent_ts), µs
#   bid_px/bid_sz float64[n_lob, depth]    — level 0..depth-1, 0 = empty
#   ask_px/ask_sz float64[n_lob, depth]
#   trade_ts      int64  [n_trade]         — exchange time (timestamp), µs
#   trade_is_sell uint8  [n_trade]         — 1 = aggressive sell hitting bids
#   trade_price   float64[n_trade]
#   trade_size    float64[n_trade]
#
# Both streams are sorted ascending by their exchange timestamp so the engine's
# two-pointer merge sees a monotonic time axis.
# ─────────────────────────────────────────────────────────────────────────────

PathArg = str | Path | Iterable[str | Path]


class LighterFeed:
    """Loads `depth` levels of Lighter LOB + trades into engine-ready arrays."""

    def __init__(self, lob_paths: PathArg, trades_paths: PathArg, depth: int = 3):
        if not 1 <= depth <= MAX_LOB_LEVELS:
            raise ValueError(f"depth must be in [1, {MAX_LOB_LEVELS}], got {depth}")
        self.depth = depth
        self._load_lob(lob_paths)
        self._load_trades(trades_paths)

    # ── loading ───────────────────────────────────────────────────────────────

    def _load_lob(self, lob_paths: PathArg) -> None:
        cols = ["sent_ts"]
        for i in range(1, self.depth + 1):
            cols += [f"bid_px_{i}", f"bid_sz_{i}", f"ask_px_{i}", f"ask_sz_{i}"]

        lob = _read_lighter("LobReader", lob_paths, columns=cols)
        lob = lob.sort_values("sent_ts", kind="stable")

        self.lob_ts = lob["sent_ts"].to_numpy(np.int64)
        self.bid_px = _level_grid(lob, "bid_px", self.depth)
        self.bid_sz = _level_grid(lob, "bid_sz", self.depth)
        self.ask_px = _level_grid(lob, "ask_px", self.depth)
        self.ask_sz = _level_grid(lob, "ask_sz", self.depth)

    def _load_trades(self, trades_paths: PathArg) -> None:
        tr = _read_lighter("TradesReader", trades_paths)
        tr = tr.dropna(subset=["timestamp", "price", "size", "is_maker_ask"])
        tr = tr.sort_values("timestamp", kind="stable")

        # is_maker_ask: the resting order was an ask, so the aggressor bought.
        # is_sell (aggressor sells, hitting bids) is therefore its negation.
        is_maker_ask = tr["is_maker_ask"].to_numpy(bool)

        self.trade_ts      = tr["timestamp"].to_numpy(np.int64)
        self.trade_is_sell = (~is_maker_ask).astype(np.uint8)
        self.trade_price   = tr["price"].to_numpy(np.float64)
        self.trade_size    = tr["size"].to_numpy(np.float64)

    # ── engine handoff ──────────────────────────────────────────────────────────

    def arrays(self) -> dict:
        """Keyword arguments for _engine.run_arrays (see bindings.cpp)."""
        return {
            "lob_ts": self.lob_ts,
            "bid_px": self.bid_px, "bid_sz": self.bid_sz,
            "ask_px": self.ask_px, "ask_sz": self.ask_sz,
            "trade_ts": self.trade_ts, "trade_is_sell": self.trade_is_sell,
            "trade_price": self.trade_price, "trade_size": self.trade_size,
        }

    def __repr__(self) -> str:
        def span(ts):
            if len(ts) == 0:
                return "empty"
            lo, hi = pd.to_datetime([ts[0], ts[-1]], unit="us")
            return f"{lo} → {hi}"
        return (f"LighterFeed(depth={self.depth}, "
                f"lob={len(self.lob_ts):,} snapshots [{span(self.lob_ts)}], "
                f"trades={len(self.trade_ts):,} [{span(self.trade_ts)}])")


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_lighter(reader_name: str, paths: PathArg, **kwargs) -> pd.DataFrame:
    """Import tools lazily: only feed users need research/tools on the path."""
    try:
        from tools.readers import lighter
    except ImportError as e:
        raise ImportError(
            "LighterFeed needs the research readers (tools.readers.lighter). "
            "Run from the research/ directory or add the repo root to sys.path."
        ) from e
    return getattr(lighter, reader_name)(paths, **kwargs).load()


def _level_grid(df: pd.DataFrame, prefix: str, depth: int) -> np.ndarray:
    """Stack columns {prefix}_1 .. {prefix}_depth into a [n, depth] grid."""
    cols = [f"{prefix}_{i}" for i in range(1, depth + 1)]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(
            f"LighterFeed: LOB columns not found: {missing[:3]}... "
            f"(expected {prefix}_1..{prefix}_{depth})"
        )
    return np.ascontiguousarray(df[cols].to_numpy(np.float64))
