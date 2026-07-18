"""Склейка lob Lighter в один pandas DataFrame."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .lob_raw import LobReaderRaw


class LobReader:
    """
    Те же аргументы, что у LobReaderRaw. Возвращает один DataFrame —
    конкатенацию всех parquet-файлов в порядке передачи, as-is.

    Колонки как в файле: sent_ts, recv_ts (мкс) + ask/bid_px/sz_1..30
    (1-индексно, 30 уровней; пустые уровни — нули). Данные не меняем.

    columns: подмножество колонок для чтения (см. LobReaderRaw). None — все.
    """

    def __init__(self, files: str | Path | Iterable[str | Path],
                 columns: list[str] | None = None) -> None:
        self._raw = LobReaderRaw(files, columns=columns)

    def load(self) -> pd.DataFrame:
        return pd.concat(list(self._raw), ignore_index=True)
