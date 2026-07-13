"""Парсит сырой поток markPrice Binance в pandas DataFrame: одна строка = один снимок."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .mark_price_raw import MarkPriceReaderRaw

# Фиксированный порядок колонок: снимок mark/index/funding, раз в секунду.
COLUMNS = [
    # ── время ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    "timestamp",           # мкс, время события (data.E)
    # "symbol",              # data.s
    # ── цены (str -> float) ──
    "mark_price",          # data.p
    "index_price",         # data.i
    # "mark_price_ma",       # data.ap — скользящая средняя марк-прайса
    # "estimated_settle_price",  # data.P
    # ── фандинг ──
    "funding_rate",        # data.r
    "next_funding_time",   # data.T — мс, как есть; СМ. докстринг
]


def to_float(value):
    """Ценовые/рейтовые поля приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


def to_micros(value):
    """Метки Binance приходят в миллисекундах; приводим к мкс."""
    return value * 1000 if value is not None else None


class MarkPriceReader:
    """
    Те же аргументы, что у MarkPriceReaderRaw. Возвращает DataFrame, где одна
    строка = одно сообщение markPrice, в порядке поступления из raw.

    Полезная нагрузка лежит под ключом "data" (обёртка combined-стрима);
    receive_timestamp коллектор кладёт на верхний уровень.

    ВНИМАНИЕ, поле ``T``. В этом стриме оно означает НЕ время транзакции (как в
    bookTicker и aggTrade), а время СЛЕДУЮЩЕГО фандинга — метку в будущем.
    Поэтому колонка называется ``next_funding_time``, а не ``transaction_time``.

    Это также НЕ аналог ``funding_timestamp`` у Lighter: там метка ТЕКУЩЕГО
    цикла фандинга (в прошлом). Напрямую сравнивать их нельзя.

    Напрямую сопоставимы с lighter.MarketStatsReader только ``mark_price``,
    ``index_price`` и ``funding_rate``. Остального (mid/best/open_interest,
    дневные метрики) в этом стриме нет — оно живёт в ``@ticker``, который мы
    не собираем.

    Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = MarkPriceReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            data = msg.get("data", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                "timestamp": to_micros(data.get("E")),
                # "symbol": data.get("s"),
                "mark_price": to_float(data.get("p")),
                "index_price": to_float(data.get("i")),
                # "mark_price_ma": to_float(data.get("ap")),
                # "estimated_settle_price": to_float(data.get("P")),
                "funding_rate": to_float(data.get("r")),
                "next_funding_time": data.get("T"),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
