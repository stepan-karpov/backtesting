"""Сырой поток строк JSON trades из lz4."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from ._io import coerce_paths, iter_lines_chain


class TradesReaderRaw:
    """
    Один или несколько lz4 с JSONL по сделкам — итерация по **строкам** подряд
    (в порядке файлов).
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = coerce_paths(files)

    def __iter__(self) -> Iterator[str]:
        yield from iter_lines_chain(self._paths)
