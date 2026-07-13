"""Парсит сырой поток forceOrder Binance в pandas DataFrame: одна строка = одна ликвидация."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .liquidations_raw import LiquidationsReaderRaw

# Фиксированный порядок колонок. Значения кладём как в источнике, без интерпретаций.
COLUMNS = [
    # ── время ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    "timestamp",           # мкс, время события (data.E)
    "transaction_time",    # мкс, время сделки (order.T)
    # ── ликвидационный ордер ──
    "side",                # order.S — сырое "BUY" / "SELL"; СМ. докстринг
    "price",               # order.p — цена ордера, str -> float
    "avg_price",           # order.ap — фактическая средняя цена исполнения
    "size",                # order.q — исходный объём
    "filled_size",         # order.z — накопленный исполненный объём
    "order_status",        # order.X
    # "last_filled_size",    # order.l
    # "order_type",          # order.o
    # "time_in_force",       # order.f
    # "symbol",              # order.s
]


def to_float(value):
    """Цены/размеры приходят строками; None оставляем None -> NaN."""
    return float(value) if value is not None else None


def to_micros(value):
    """Метки Binance приходят в миллисекундах; приводим к мкс."""
    return value * 1000 if value is not None else None


class LiquidationsReader:
    """
    Те же аргументы, что у LiquidationsReaderRaw. Возвращает DataFrame, где одна
    строка = одна ликвидация, в порядке поступления из raw.

    Структура сообщения глубже, чем у остальных стримов: сам ордер лежит под
    ``data.o`` (msg -> data -> o). Внутри ордера ключ ``o`` — это тип ордера,
    не путать с внешним.

    ВНИМАНИЕ, сторона. ``side`` кладём сырым, но смысл обратный интуитивному:
    ликвидационный ордер идёт ПРОТИВ позиции, которую закрывают.

        side == "BUY"  -> ликвидировали ШОРТ (принудительный выкуп)
        side == "SELL" -> ликвидировали ЛОНГ

    Ликвидации редкие: часы без единой ликвидации не имеют файла вовсе, и такие
    пути LiquidationsReaderRaw просто пропускает.

    Колонки: см. COLUMNS.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = LiquidationsReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)
            data = msg.get("data", {})
            order = data.get("o", {})

            rows.append({
                "receive_timestamp": msg.get("receive_timestamp"),
                "timestamp": to_micros(data.get("E")),
                "transaction_time": to_micros(order.get("T")),
                "side": order.get("S"),
                "price": to_float(order.get("p")),
                "avg_price": to_float(order.get("ap")),
                "size": to_float(order.get("q")),
                "filled_size": to_float(order.get("z")),
                "order_status": order.get("X"),
                # "last_filled_size": to_float(order.get("l")),
                # "order_type": order.get("o"),
                # "time_in_force": order.get("f"),
                # "symbol": order.get("s"),
            })

        return pd.DataFrame(rows, columns=COLUMNS)
