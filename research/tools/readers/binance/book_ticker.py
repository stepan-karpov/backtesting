"""Парсит сырой поток bookTicker Binance в pandas DataFrame: одна строка = одно сообщение."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .book_ticker_raw import BookTickerReaderRaw

# Фиксированный порядок колонок: top-of-book по каждому сообщению.
# Имена совпадают с lighter.TickerReader — оба венью отдают DataFrame одной
# формы, поэтому лид-лаг считается без переименований.
COLUMNS = [
    # ── уровень сообщения ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    # "update_id",           # data.u — логические часы книги (аналог nonce у Lighter)
    # "symbol",              # data.s
    "timestamp",           # мкс, время события (data.E)
    "last_updated_at",     # мкс, время обновления книги движком (data.T)
    # ── top-of-book ──
    "ask_price",           # строка -> float
    "ask_size",            # строка -> float
    "bid_price",           # строка -> float
    "bid_size",            # строка -> float
]


def to_float(value):
    """Цены/размеры приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


def to_micros(value):
    """Метки Binance приходят в миллисекундах; приводим к мкс."""
    return value * 1000 if value is not None else None


class BookTickerReader:
    """
    Те же аргументы, что у BookTickerReaderRaw. Возвращает DataFrame, где одна
    строка = одно сообщение bookTicker (top-of-book), в порядке поступления из raw.

    Полезная нагрузка лежит под ключом "data" (обёртка combined-стрима);
    receive_timestamp коллектор кладёт на верхний уровень.
    Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = BookTickerReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            data = msg.get("data", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                # "update_id": data.get("u"),
                # "symbol": data.get("s"),
                "timestamp": to_micros(data.get("E")),
                "last_updated_at": to_micros(data.get("T")),
                "ask_price": to_float(data.get("a")),
                "ask_size": to_float(data.get("A")),
                "bid_price": to_float(data.get("b")),
                "bid_size": to_float(data.get("B")),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
