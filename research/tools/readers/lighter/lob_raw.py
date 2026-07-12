"""Сырой поток lob Lighter: по одному DataFrame на parquet-файл."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from ._io import coerce_paths


class LobReaderRaw:
    """
    Один или несколько parquet-файлов lob — итерация по **файлам** подряд
    (в порядке передачи). Каждый элемент — DataFrame одного файла as-is,
    без обработки. Склейка — забота основного LobReader.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = coerce_paths(files)

    def __iter__(self) -> Iterator[pd.DataFrame]:
        for path in self._paths:
            yield pd.read_parquet(path)
