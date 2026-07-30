from __future__ import annotations

try:
    from ._engine import OrderBook, MAX_LOB_LEVELS
except ImportError as e:
    raise ImportError(
        "C++ engine not compiled.\n"
        "Run:  cd backtesting && make\n"
        "(requires: pip install pybind11)"
    ) from e

from .gateway import OrderGateway
from .strategy import Strategy
from .backtester import Backtester
from .feed import LighterFeed

__all__ = [
    "Strategy", "OrderGateway",
    "Backtester", "OrderBook", "LighterFeed", "MAX_LOB_LEVELS"
]
