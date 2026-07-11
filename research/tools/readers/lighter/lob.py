"""Парсит сырой поток LOB в pandas DataFrame."""

from __future__ import annotations

import json
from typing import Iterable

import pandas as pd
from pathlib import Path

from .lob_raw import LobReaderRaw

LEVELS = 20


def _make_columns() -> list[str]:
    cols = ["time_ms"]
    for side in ("bid", "ask"):
        for i in range(LEVELS):
            cols += [f"{side}_px_{i}", f"{side}_sz_{i}", f"{side}_n_{i}"]
    return cols


class LobReader:
    """
    Принимает те же аргументы что и LobReaderRaw.
    Возвращает pandas DataFrame с одной строкой на снапшот.

    Колонки:
      time_ms          — unix ms (из raw.data.time)
      bid_px_0..19     — цена уровня
      bid_sz_0..19     — суммарный размер на уровне
      bid_n_0..19      — количество ордеров на уровне
      ask_px_0..19     — аналогично для асков
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._raw = LobReaderRaw(files)

    def load(self) -> pd.DataFrame:
        rows = []
        for line in self._raw:
            snap = json.loads(line)
            data = snap["raw"]["data"]

            row: list = [data["time"]]

            bids, asks = data["levels"][0], data["levels"][1]

            for levels in (bids, asks):
                for i in range(LEVELS):
                    if i < len(levels):
                        row += [
                            float(levels[i]["px"]),
                            float(levels[i]["sz"]),
                            int(levels[i]["n"]),
                        ]
                    else:
                        row += [None, None, None]

            rows.append(row)

        return pd.DataFrame(rows, columns=_make_columns())