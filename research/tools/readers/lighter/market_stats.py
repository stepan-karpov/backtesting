"""Парсит сырой поток market_stats Lighter в pandas DataFrame: одна строка = один снимок."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .market_stats_raw import MarketStatsReaderRaw

# Фиксированный порядок колонок: снимок метрик рынка по каждому сообщению.
COLUMNS = [
    # ── время / привязка ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    "timestamp",           # мкс (из мс ×1000)
    # "market_id",
    # "symbol",
    # ── цены (str -> float) ──
    "index_price",
    "mark_price",
    "mid_price",
    "best_bid_price",
    "best_ask_price",
    "last_trade_price",
    # ── фандинг ──
    "funding_rate",
    "current_funding_rate",
    "funding_timestamp",   # мс, метка цикла фандинга (как есть)
    # ── открытый интерес ──
    "open_interest",
    # ── дневные метрики (как есть) ──
    "daily_base_token_volume",
    "daily_quote_token_volume",
    "daily_price_low",
    "daily_price_high",
    "daily_price_change",
]


def to_float(value):
    """Ценовые/рейтовые поля приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


class MarketStatsReader:
    """
    Те же аргументы, что у MarketStatsReaderRaw. Возвращает DataFrame, где одна
    строка = одно сообщение market_stats, в порядке поступления из raw.

    Поля берём через .get(); ценовые/рейтовые строки -> float; timestamp
    приводим к мкс (×1000). Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = MarketStatsReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            stats = msg.get("market_stats", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                "timestamp": msg.get("timestamp") * 1000,
                # "market_id": stats.get("market_id"),
                # "symbol": stats.get("symbol"),
                "index_price": to_float(stats.get("index_price")),
                "mark_price": to_float(stats.get("mark_price")),
                "mid_price": to_float(stats.get("mid_price")),
                "best_bid_price": to_float(stats.get("best_bid_price")),
                "best_ask_price": to_float(stats.get("best_ask_price")),
                "last_trade_price": to_float(stats.get("last_trade_price")),
                "funding_rate": to_float(stats.get("funding_rate")),
                "current_funding_rate": to_float(stats.get("current_funding_rate")),
                "funding_timestamp": stats.get("funding_timestamp"),
                "open_interest": to_float(stats.get("open_interest")),
                "daily_base_token_volume": stats.get("daily_base_token_volume"),
                "daily_quote_token_volume": stats.get("daily_quote_token_volume"),
                "daily_price_low": stats.get("daily_price_low"),
                "daily_price_high": stats.get("daily_price_high"),
                "daily_price_change": stats.get("daily_price_change"),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
