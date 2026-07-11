"""
Конвертирует trades parquet -> lz4 JSONL
Запускать после downloading.py

До:  {SYMBOL}/trades/YYYYMMDD/HH.parquet
После: {SYMBOL}/trades/YYYYMMDD/HH.lz4

Каждая строка в lz4 — один JSON-объект со всеми колонками исходного parquet.

Установка:
  pip install pyarrow lz4
"""

from __future__ import annotations

import datetime
import decimal
import json
import math
from pathlib import Path

import lz4.frame
import pyarrow.parquet as pq

DATA_DIR = Path("./data/hyperliquid//XPL/trades")


def _json_safe(value):
    """Приводит значение из Arrow/pyarrow к JSON-совместимому виду."""
    if value is None:
        return None
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
    except ImportError:
        pass
    if isinstance(value, (list, dict)):
        return value
    return value


def _row_to_json_obj(row: dict) -> dict:
    return {k: _json_safe(v) for k, v in row.items()}


for parquet_path in sorted(DATA_DIR.glob("*/*.parquet")):
    lz4_path = parquet_path.with_suffix(".lz4")

    if lz4_path.exists():
        continue

    table = pq.read_table(parquet_path)
    n = len(table)

    lines = []
    for row in table.to_pylist():
        lines.append(
            json.dumps(
                _row_to_json_obj(row),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    raw = "\n".join(lines).encode()
    with open(lz4_path, "wb") as f:
        f.write(lz4.frame.compress(raw))

    parquet_path.unlink()
    print(f"  {parquet_path} -> {lz4_path.name}  ({n} строк, колонок: {table.num_columns})")
