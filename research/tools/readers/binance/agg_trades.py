"""Парсит сырой поток aggTrade Binance в pandas DataFrame: одна строка = одна сделка."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .agg_trades_raw import AggTradesReaderRaw

# Фиксированный порядок колонок. Значения кладём как в источнике, без интерпретаций.
COLUMNS = [
    # ── уровень сообщения ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    "timestamp",           # мкс, время события (data.E) — когда биржа отправила
    "transaction_time",    # мкс, время самой сделки (data.T); может отставать от E
    # ── уровень сделки ──
    "agg_trade_id",        # data.a — ключ дедупа/сортировки
    "price",               # строка -> float
    "size",                # строка -> float (data.q)
    # "normal_size",         # data.nq — размер без RPI-ордеров
    "is_buyer_maker",      # data.m — сырое поле, СМ. докстринг про инверсию
    "first_trade_id",      # data.f — по паре f/l видно, сколько филлов схлопнулось
    "last_trade_id",       # data.l
    # "symbol",              # data.s
]


def to_float(value):
    """Цены/размеры приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


def to_micros(value):
    """Метки Binance приходят в миллисекундах; приводим к мкс."""
    return value * 1000 if value is not None else None


class AggTradesReader:
    """
    Те же аргументы, что у AggTradesReaderRaw. Возвращает DataFrame, где одна
    строка = одна агрегированная сделка, в порядке поступления из raw.

    Полезная нагрузка лежит под ключом "data" (обёртка combined-стрима);
    receive_timestamp коллектор кладёт на верхний уровень.

    ВНИМАНИЕ, сторона агрессора. ``is_buyer_maker`` (data.m) — сырое поле Binance:
    True означает, что мейкером был ПОКУПАТЕЛЬ, т.е. мейкер стоял в биде, а
    агрессор продавал. Это логическая инверсия ``is_maker_ask`` у Lighter:

        is_maker_ask (Lighter) == not is_buyer_maker (Binance)

    Не путать при кросс-венью сравнении order flow — знак перевернётся.

    Сделки агрегированы: филлы по одной цене и одной стороне схлопнуты в одну
    запись (диапазон исходных сделок — ``first_trade_id``..``last_trade_id``).
    Пофилльной гранулярности, как у Lighter, Binance публично не отдаёт.

    Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = AggTradesReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            data = msg.get("data", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                "timestamp": to_micros(data.get("E")),
                "transaction_time": to_micros(data.get("T")),
                "agg_trade_id": data.get("a"),
                "price": to_float(data.get("p")),
                "size": to_float(data.get("q")),
                # "normal_size": to_float(data.get("nq")),
                "is_buyer_maker": data.get("m"),
                "first_trade_id": data.get("f"),
                "last_trade_id": data.get("l"),
                # "symbol": data.get("s"),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
