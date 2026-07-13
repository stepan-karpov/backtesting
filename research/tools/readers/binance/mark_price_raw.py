"""Сырой поток строк JSON markPrice из zst."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from ._io import coerce_paths, iter_lines_chain


class MarkPriceReaderRaw:
    """
    Один или несколько .jsonl.zst с markPrice — итерация по **строкам** подряд
    (в порядке файлов). Каждая строка = один снимок mark/index/funding;
    JSON не парсим — разбор делает основной MarkPriceReader.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = coerce_paths(files)

    def __iter__(self) -> Iterator[str]:
        yield from iter_lines_chain(self._paths)
