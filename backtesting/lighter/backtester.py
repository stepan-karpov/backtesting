from __future__ import annotations

from .strategy import Strategy

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
    ):
        # Round-trip order latency: a quote decided at exchange time T lands at
        # T + latency_us. See engine/backtester.hpp for the in-flight model.
        self._latency_us = int(latency_us)
        self.log_interval_us = int(log_interval_sec * 1_000_000)
        self.quote_log_stride = max(1, int(quote_log_stride))

    def run(self, strategy: Strategy, feed, output_path: str = "result") -> str:
        """Run the simulation on `feed`; saves CSVs with prefix output_path.

        `feed` is any object exposing .arrays() (see LighterFeed). Returns the
        output prefix.
        """
        _engine.run_arrays(
            strategy,
            **feed.arrays(),
            latency_us=self._latency_us,
            log_interval_us=self.log_interval_us,
            quote_log_stride=self.quote_log_stride,
            output_path=output_path,
        )
        return output_path
