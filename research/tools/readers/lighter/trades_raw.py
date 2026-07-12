"""Сырой поток строк JSON trades из zst."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from ._io import coerce_paths, iter_lines_chain


class TradesReaderRaw:
    """
    Один или несколько .jsonl.zst с trades — итерация по **строкам** подряд
    (в порядке файлов). Каждая строка = одно WS-сообщение (батч сделок);
    JSON не парсим — разбор и разворот батча делает основной TradesReader.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = coerce_paths(files)

    def __iter__(self) -> Iterator[str]:
        yield from iter_lines_chain(self._paths)
