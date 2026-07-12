"""Парсит сырой поток ticker Lighter в pandas DataFrame: одна строка = одно сообщение."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .ticker_raw import TickerReaderRaw

# Фиксированный порядок колонок: top-of-book по каждому сообщению.
COLUMNS = [
    # ── уровень сообщения ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    # "nonce",               # логические часы движка (джойн с trades по nonce)
    # "msg_type",            # "update" / "subscribed" — префикс msg["type"]
    "timestamp",           # мкс, время сообщения
    "last_updated_at",     # мкс, время обновления top-of-book движком
    # "market_id",           # из channel "ticker:<id>"
    # ── top-of-book ──
    # "symbol",              # ticker.s
    "ask_price",           # строка -> float
    "ask_size",            # строка -> float
    "bid_price",           # строка -> float
    "bid_size",            # строка -> float
]


def to_float(value):
    """Цены/размеры приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


def market_id_from_channel(channel):
    """"ticker:3" -> 3; при неожиданном формате -> None."""
    parts = channel.split(":") if channel else []
    return int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else None


class TickerReader:
    """
    Те же аргументы, что у TickerReaderRaw. Возвращает DataFrame, где одна
    строка = одно сообщение ticker (top-of-book), в порядке поступления из raw.

    Поля берём через .get(); цены/размеры str->float; market_id — из channel.
    Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = TickerReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            ticker = msg.get("ticker", {})
            best_ask = ticker.get("a", {})
            best_bid = ticker.get("b", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                # "nonce": msg.get("nonce"),
                # "msg_type": msg.get("type", "").split("/")[0],
                "timestamp": msg.get("timestamp") * 1000,
                "last_updated_at": msg.get("last_updated_at"),
                # "market_id": market_id_from_channel(msg.get("channel")),
                # "symbol": ticker.get("s"),
                "ask_price": to_float(best_ask.get("price")),
                "ask_size": to_float(best_ask.get("size")),
                "bid_price": to_float(best_bid.get("price")),
                "bid_size": to_float(best_bid.get("size")),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
