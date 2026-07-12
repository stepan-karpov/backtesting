"""Instruments: readers, visualization helpers."""

from pathlib import Path

# Корень репозитория = ближайший родитель с .git. Не зависит от CWD и не хардкод:
# пути к данным строим от него — ROOT / "data/lighter/..." — работает откуда угодно.
ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())

__all__ = ["ROOT"]
