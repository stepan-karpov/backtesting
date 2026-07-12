"""Парсит сырой поток trades Lighter в pandas DataFrame: одна строка = одна сделка."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .trades_raw import TradesReaderRaw

# Фиксированный порядок колонок (21 признак из схемы; 22 колонки — у #21 два
# поля времени). Значения кладём как в источнике, без интерпретаций.
COLUMNS = [
    # ── уровень сообщения (размножается на каждую сделку батча) ──
    "receive_timestamp",   # локальные часы приёма фида, мкс
    "timestamp",           # мкс, время матча
    "transaction_time",    # мкс, время транзакции
    # "nonce",               # логические часы движка (джойн с ticker/lob по nonce)
    # "msg_type",            # "update" / "subscribed" — префикс msg["type"]
    # ── уровень сделки ──
    "trade_id",            # ключ дедупа/сортировки
    "type",                # "trade" / "liquidation" / "deleverage" / ...
    # "market_id",
    "price",               # строка -> float
    "size",                # строка -> float (нотионал = price*size, не храним)
    "is_maker_ask",        # сторона агрессора
    "ask_account_id",
    "bid_account_id",
    "ask_id",
    "bid_id",
    "taker_fee",           # сырой int; ОТСУТСТВУЕТ = 0 = Standard
    "maker_fee",           # сырой int
    # "integrator_taker_fee",
    # "integrator_maker_fee",
    "taker_position_size_before",  # строка -> float
    "maker_position_size_before",  # строка -> float
    "block_height",
]


def _to_float(x):
    """Цены/размеры приходят строками ("0.16280"); None оставляем None -> NaN."""
    return float(x) if x is not None else None


class TradesReader:
    """
    Те же аргументы, что у TradesReaderRaw. Возвращает DataFrame, где одна
    строка = одна сделка, в порядке поступления из raw.

    Оба массива сообщения — ``trades`` и ``liquidation_trades`` — разворачиваются
    в единый поток (для каждого сообщения сначала trades, затем liquidation_trades);
    вид сделки различается колонкой ``type``.

    Поля берём через ``.get()``: набор ключей в записи варьируется (у ликвидаций
    нет integrator-полей, ``*_sign_changed`` приходит только для сменившей знак
    стороны и т.п.). По явной договорённости ``taker_fee`` при отсутствии = 0
    (Standard); остальные отсутствующие поля -> NaN.

    Единицы комиссий (ppm?) и семантика системных account_id — UNVERIFIED,
    подлежат фиксации в docs/FACTS.md.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = TradesReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            msg = json.loads(line)

            # общие для всех сделок сообщения поля
            recv = msg.get("receive_timestamp")
            nonce = msg.get("nonce")
            msg_type = msg.get("type", "").split("/")[0]  # "update" / "subscribed"

            for t in msg.get("trades", []) + msg.get("liquidation_trades", []):
                rows.append({
                    "receive_timestamp": recv,
                    "timestamp": t.get("timestamp") * 1000,
                    "transaction_time": t.get("transaction_time"),
                    # "nonce": nonce,
                    # "msg_type": msg_type,
                    "trade_id": t.get("trade_id"),
                    "type": t.get("type"),
                    # "market_id": t.get("market_id"),
                    "price": _to_float(t.get("price")),
                    "size": _to_float(t.get("size")),
                    "is_maker_ask": t.get("is_maker_ask"),
                    "ask_account_id": t.get("ask_account_id"),
                    "bid_account_id": t.get("bid_account_id"),
                    "ask_id": t.get("ask_id"),
                    "bid_id": t.get("bid_id"),
                    "taker_fee": t.get("taker_fee", 0),  # отсутствует = 0 = Standard
                    "maker_fee": t.get("maker_fee", 0),
                    # "integrator_taker_fee": t.get("integrator_taker_fee"),
                    # "integrator_maker_fee": t.get("integrator_maker_fee"),
                    "taker_position_size_before": _to_float(t.get("taker_position_size_before")),
                    "maker_position_size_before": _to_float(t.get("maker_position_size_before")),
                    "block_height": t.get("block_height"),
                })

        return pd.DataFrame(rows, columns=COLUMNS)
