"""Сырой поток строк JSON LOB из lz4."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from ._io import coerce_paths, iter_lines_chain


class LobReaderRaw:
    """
    Одна или несколько lz4 с LOB (по строке на снимок в каждом файле).

    ``files`` — строка пути, :class:`~pathlib.Path` или **перечисление** путей
    (список / кортеж строк); порядок файлов = порядок строк в потоке.

    Итерирует **строки** JSON без парсинга.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = coerce_paths(files)

    def __iter__(self) -> Iterator[str]:
        yield from iter_lines_chain(self._paths)
