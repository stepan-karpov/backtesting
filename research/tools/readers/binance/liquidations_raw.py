"""Сырой поток строк JSON forceOrder из zst."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from ._io import coerce_paths, iter_lines_chain


class LiquidationsReaderRaw:
    """
    Один или несколько .jsonl.zst с forceOrder — итерация по **строкам** подряд
    (в порядке файлов). Каждая строка = одна ликвидация;
    JSON не парсим — разбор делает основной LiquidationsReader.

    Несуществующие пути ПРОПУСКАЮТСЯ. Ликвидации редкие, а коллектор создаёт
    часовой файл только когда пришло хоть одно сообщение — поэтому отсутствие
    файла означает "за этот час ликвидаций не было", а не потерю данных.
    Падать на таком часе бессмысленно: для этого канала дырки — норма.
    """

    def __init__(self, files: str | Path | Iterable[str | Path]) -> None:
        self._paths = [p for p in coerce_paths(files) if p.exists()]

    def __iter__(self) -> Iterator[str]:
        yield from iter_lines_chain(self._paths)
