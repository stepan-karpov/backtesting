"""Парсит сырой поток trades в pandas DataFrame."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .trades_raw import TradesReaderRaw

COLUMNS = ["time_ms", "tid", "px", "sz", "side", "crossed", "fee", "user", "dir", "startPosition"]


class TradesReader:
    """
    Принимает те же аргументы что и TradesReaderRaw.
    Возвращает pandas DataFrame с одной строкой на сделку.

    Колонки:
      time_ms       — unix ms (нативное разрешение Hyperliquid; микросекундный
                      хвост в исходном поле time всегда 000)
      tid           — id матча (одинаковый для taker и maker leg одного фила)
      px            — цена сделки
      sz            — размер в SOL
      side          — "B" (buy) или "A" (sell)
      crossed       — True если taker, False если maker
      fee           — комиссия в USDC (отрицательная = top-tier maker rebate)
      user          — адрес трейдера
      dir           — "Open Long" / "Close Long" / "Open Short" / "Close Short"
      startPosition — размер позиции трейдера до сделки
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = TradesReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            t = json.loads(line)
            rows.append([
                t["time"],
                int(t["tid"]),
                float(t["px"]),
                float(t["sz"]),
                t["side"],
                bool(t["crossed"]),
                float(t["fee"]),
                t["user"],
                t["dir"],
                float(t["startPosition"]),
            ])

        df = pd.DataFrame(rows, columns=COLUMNS)
        # ISO → unix ms одной векторной операцией; быстрее и надёжнее построчного парсинга
        # часть строк без дробной части (e.g. "2026-04-01T00:02:26") — нужен ISO8601 mode.
        # Принудительно кастуем к datetime64[ms]: иначе pandas 2.x инферит unit по
        # точности строки (s/ms/us) и .astype(int64) даёт несогласованные значения.
        df["time_ms"] = pd.to_datetime(df["time_ms"], format="ISO8601") \
                          .astype("datetime64[ms]").astype("int64")
        return df