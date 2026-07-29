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

    def __init__(self, lob_paths: PathArg, trades_paths: PathArg, depth: int = 15):
        if not 1 <= depth <= MAX_LOB_LEVELS:
            raise ValueError(f"depth must be in [1, {MAX_LOB_LEVELS}], got {depth}")
        self.depth = depth
        self._load_lob(lob_paths)
        self._load_trades(trades_paths)

    # ── loading ───────────────────────────────────────────────────────────────

    def _load_lob(self, lob_paths: PathArg) -> None:
        # Stream the LOB file-by-file into pre-allocated arrays. The reader's
        # LobReader.load() would pd.concat every file into one DataFrame first,
        # then a sort copy, then four grid copies — a ~5x peak over the final
        # arrays. Here the peak is just the final arrays plus one file's frame.
        import pyarrow.parquet as pq

        depth = self.depth
        bid_px_c = [f"bid_px_{i}" for i in range(1, depth + 1)]
        bid_sz_c = [f"bid_sz_{i}" for i in range(1, depth + 1)]
        ask_px_c = [f"ask_px_{i}" for i in range(1, depth + 1)]
        ask_sz_c = [f"ask_sz_{i}" for i in range(1, depth + 1)]
        cols = ["sent_ts"] + bid_px_c + bid_sz_c + ask_px_c + ask_sz_c

        paths = _as_path_list(lob_paths)
        LobReaderRaw = _lighter_readers().LobReaderRaw

        # Row counts from the parquet footers only (no data read) → exact size to
        # pre-allocate, so the fill needs no concatenation.
        n = sum(pq.ParquetFile(str(p)).metadata.num_rows for p in paths)

        self.lob_ts = np.empty(n, np.int64)
        self.bid_px = np.empty((n, depth), np.float32)   # float32: half the RAM (guarded below)
        self.bid_sz = np.empty((n, depth), np.float32)
        self.ask_px = np.empty((n, depth), np.float32)
        self.ask_sz = np.empty((n, depth), np.float32)

        off = 0
        max_price = 0.0        # largest price seen (float64), for the precision guard
        top_uniques = []       # distinct best bid/ask prices (float64), to infer the tick
        for df in LobReaderRaw(paths, columns=cols):   # one file at a time
            k = len(df)
            self.lob_ts[off:off + k] = df["sent_ts"].to_numpy(np.int64)
            bpx = df[bid_px_c].to_numpy(np.float64)     # this file's prices, float64, for the guard
            apx = df[ask_px_c].to_numpy(np.float64)
            self.bid_px[off:off + k] = bpx              # float64 → float32 on assignment
            self.ask_px[off:off + k] = apx
            self.bid_sz[off:off + k] = df[bid_sz_c].to_numpy(np.float32)
            self.ask_sz[off:off + k] = df[ask_sz_c].to_numpy(np.float32)
            m = max(bpx.max(initial=0.0), apx.max(initial=0.0))
            if m > max_price:
                max_price = m
            top_uniques.append(np.unique(np.concatenate([bpx[:, 0], apx[:, 0]])))
            off += k
            del df, bpx, apx

        if off != n:                                   # defensive: fewer rows than the footer claimed
            self.lob_ts = self.lob_ts[:off]
            self.bid_px, self.bid_sz = self.bid_px[:off], self.bid_sz[:off]
            self.ask_px, self.ask_sz = self.ask_px[:off], self.ask_sz[:off]

        # Files arrive in chronological order and each is internally sorted, so the
        # concatenation is already ascending in sent_ts. Sort only if that is ever
        # violated (identical result to the old unconditional stable sort).
        if self.lob_ts.size and not (np.diff(self.lob_ts) >= 0).all():
            order = np.argsort(self.lob_ts, kind="stable")
            self.lob_ts = self.lob_ts[order]
            self.bid_px, self.bid_sz = self.bid_px[order], self.bid_sz[order]
            self.ask_px, self.ask_sz = self.ask_px[order], self.ask_sz[order]

        self._check_float32_precision(max_price, top_uniques)

    # ── float32 precision guard ─────────────────────────────────────────────────

    _F32_MARGIN = 0.05    # max allowed float32 ULP as a fraction of the price tick

    def _check_float32_precision(self, max_price: float, top_uniques: list) -> None:
        """Fail loudly if float32 storage would blur the price tick.

        float32's step (ULP) grows with magnitude: at the largest price it is
        max_price·2**-23. If that reaches _F32_MARGIN of the tick, a price can round
        toward a neighbouring tick and mid / spread / bps metrics drift. The tick is
        inferred from the data — the smallest gap between distinct best bid/ask prices
        — so no exchange fact is assumed. Raised before the feed is used; switch that
        symbol to a float64 feed if it fires. Sizes are not guarded (low magnitude,
        negligible metric impact — see review note).
        """
        if not top_uniques:
            return
        u = np.unique(np.concatenate(top_uniques))
        u = u[u > 0.0]
        if u.size < 2:
            return                                   # single price → no tick to infer
        tick = float(np.diff(u).min())               # smallest price increment in the data
        max_ulp = float(max_price) * 2.0 ** -23      # float32 step at the largest price
        if max_ulp >= self._F32_MARGIN * tick:
            raise ValueError(
                f"LighterFeed(depth={self.depth}): float32 would blur the price tick. "
                f"ULP at max price {max_price:.6g} is {max_ulp:.3e}, not below "
                f"{self._F32_MARGIN}·tick = {self._F32_MARGIN * tick:.3e} "
                f"(inferred tick {tick:.3e}). price/tick = {max_price / tick:.2e} exceeds the "
                f"float32 limit ≈ {self._F32_MARGIN * 2 ** 23:.2e}; use a float64 feed for this symbol."
            )

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

def _lighter_readers():
    """Import the research Lighter readers lazily — only feed users need them."""
    try:
        from tools.readers import lighter
    except ImportError as e:
        raise ImportError(
            "LighterFeed needs the research readers (tools.readers.lighter). "
            "Run from the research/ directory or add the repo root to sys.path."
        ) from e
    return lighter


def _read_lighter(reader_name: str, paths: PathArg, **kwargs) -> pd.DataFrame:
    return getattr(_lighter_readers(), reader_name)(paths, **kwargs).load()


def _as_path_list(paths: PathArg) -> list[Path]:
    if isinstance(paths, (str, Path)):
        return [Path(paths)]
    return [Path(p) for p in paths]
