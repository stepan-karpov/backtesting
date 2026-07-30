from __future__ import annotations

from .strategy import Strategy
from .persistence import save_run

try:
    from . import _engine
except ImportError:
    raise ImportError("C++ engine not compiled.\nRun:  cd backtesting && make")


class Backtester:
    """Thin wrapper — the hot loop runs entirely in C++.

    Holds the run configuration (latency, logging); market data is supplied
    per run() as a feed (e.g. LighterFeed) of normalised in-memory arrays.
    """

    def __init__(
        self,
        latency_us: int = 0,
        log_interval_sec: float = 10.0,
        quote_log_stride: int = 50,
        fee_bps: float = 0.0,
    ):
        # Round-trip order latency: a quote decided at exchange time T lands at
        # T + latency_us. See engine/backtester.hpp for the in-flight model.
        self._latency_us = int(latency_us)
        self.log_interval_us = int(log_interval_sec * 1_000_000)
        self.quote_log_stride = max(1, int(quote_log_stride))
        # Per-fill fee as bps of notional, charged online in the engine (fill_fee column,
        # net PnL). Baked into the run — different fees mean different runs. 0 = fee-free.
        self.fee_bps = float(fee_bps)

    def run(self, strategy: Strategy, feed, output_path: str = "result") -> str:
        """Run the simulation on `feed`; persist the result and return its prefix.

        `feed` is any object exposing .arrays() (see LighterFeed). Every run is written to
        disk as ``{output_path}_{pnl,quotes,fills,quota}.parquet`` (typed/binary — see
        persistence.py); load it back with ``BacktestResult(prefix)``. The engine hands
        its columns to Python in memory; turning them into files happens here.
        """
        arrays = _engine.run_arrays(
            strategy,
            **feed.arrays(),
            latency_us=self._latency_us,
            log_interval_us=self.log_interval_us,
            quote_log_stride=self.quote_log_stride,
            fee_bps=self.fee_bps,
        )
        return save_run(arrays, output_path)
