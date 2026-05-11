"""Декомпрессия lz4 и склейка путей (один или несколько файлов)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

import lz4.frame


def iter_lines_one_file(path: Path) -> Iterator[str]:
    with open(path, "rb") as f:
        blob = lz4.frame.decompress(f.read())
    for line in blob.decode().splitlines():
        if line.strip():
            yield line


def coerce_paths(files: str | Path | Iterable[str | Path]) -> list[Path]:
    """Один путь или несколько; str не трактуем как iterable символов."""
    if isinstance(files, (str, Path)):
        return [Path(files)]
    return [Path(p) for p in files]


def iter_lines_chain(paths: list[Path]) -> Iterator[str]:
    for p in paths:
        yield from iter_lines_one_file(p)
