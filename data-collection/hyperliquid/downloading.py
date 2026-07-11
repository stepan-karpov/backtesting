"""
Hyperliquid Data Downloader
────────────────────────────────
Берёт trades из уже скачанных файлов (data/all_trades),
фильтрует по COIN и сохраняет вместе с LOB.

Результат:
  ./data/COIN/lob/YYYYMMDD/HH.lz4       — LOB снапшоты
  ./data/COIN/trades/YYYYMMDD/HH.parquet — Trades, только COIN

Установка:
  pip install boto3 pyarrow

AWS credentials:
  aws configure
"""

import boto3
import pyarrow.parquet as pq
import pyarrow.compute as pc
from datetime import datetime, timedelta
from pathlib import Path

# ── Настройки ─────────────────────────────────────────────────────────────────

COIN            = "XYZ100"
DATE_FROM       = datetime(2026, 4, 1)
DATE_TO         = datetime(2026, 4, 5)
OUTPUT_DIR      = Path(f"data/hyperliquid/{COIN}")
ALL_TRADES_DIR  = Path("data/hyperliquid/all_trades")

# ── S3 helper ─────────────────────────────────────────────────────────────────

def s3_download(s3, bucket, key, local_path):
    if local_path.exists():
        return True
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        s3.download_file(bucket, key, str(local_path),
                         ExtraArgs={"RequestPayer": "requester"})
        return True
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise

# ── LOB ───────────────────────────────────────────────────────────────────────

def download_lob():
    s3     = boto3.client("s3")
    bucket = "hyperliquid-archive"

    current = DATE_FROM
    while current <= DATE_TO:
        date_str   = current.strftime("%Y%m%d")
        downloaded = 0
        for hour in range(24):
            key   = f"market_data/{date_str}/{hour}/l2Book/{COIN}.lz4"
            local = OUTPUT_DIR / "lob" / date_str / f"{hour:02d}.lz4"
            if s3_download(s3, bucket, key, local):
                downloaded += 1
        print(f"  LOB {date_str}: {downloaded}/24 часов")
        current += timedelta(days=1)

# ── Trades ────────────────────────────────────────────────────────────────────

def filter_and_save(src_path: Path, out_path: Path):
    table    = pq.read_table(src_path)
    filtered = table.filter(pc.equal(table["coin"], COIN))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(filtered, out_path, compression="snappy")


def filter_trades():
    current = DATE_FROM
    while current <= DATE_TO:
        date_str   = current.strftime("%Y%m%d")
        processed  = 0

        for hour in range(24):
            hh       = f"{hour:02d}"
            src_path = ALL_TRADES_DIR / date_str / f"{hh}.parquet"
            out_path = OUTPUT_DIR / "trades" / date_str / f"{hh}.parquet"

            if out_path.exists():
                processed += 1
                continue

            if not src_path.exists():
                continue

            filter_and_save(src_path, out_path)
            processed += 1

        print(f"  Trades {date_str}: {processed}/24 файлов")
        current += timedelta(days=1)

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== LOB (hyperliquid-archive) ===")
    download_lob()

    print(f"\n=== Trades (фильтрация {COIN} из {ALL_TRADES_DIR}) ===")
    filter_trades()