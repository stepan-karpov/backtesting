"""Декомпрессия zstd и склейка путей (один или несколько файлов)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, Iterator

import zstandard as zstd


def iter_lines_one_file(path: Path) -> Iterator[str]:
    # stream_reader (а не decompress(f.read())): файлы сжаты потоково через
    # copy_stream, размер распакованных данных в кадре может отсутствовать —
    # тогда однопроходный decompress падает. Плюс не держим файл в памяти.
    with open(path, "rb") as f, zstd.ZstdDecompressor().stream_reader(f) as reader:
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            if line.strip():
                yield line.rstrip("\n")


def coerce_paths(files: str | Path | Iterable[str | Path]) -> list[Path]:
    """Один путь или несколько; str не трактуем как iterable символов."""
    if isinstance(files, (str, Path)):
        return [Path(files)]
    return [Path(p) for p in files]


def iter_lines_chain(paths: list[Path]) -> Iterator[str]:
    for p in paths:
        yield from iter_lines_one_file(p)
