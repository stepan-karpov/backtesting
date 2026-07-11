"""
Hyperliquid Trades Raw Downloader
──────────────────────────────────
Скачивает все trades (по всем монетам) из Artemis без фильтрации.

Результат:
  ./hl_data/trades/YYYYMMDD/HH.parquet — оригинальные файлы Artemis

Установка:
  pip install boto3

AWS credentials:
  aws configure
"""

import boto3
from datetime import datetime, timedelta
from pathlib import Path

# ── Настройки ─────────────────────────────────────────────────────────────────

DATE_FROM  = datetime(2026, 4, 1)
DATE_TO    = datetime(2026, 4, 5)
OUTPUT_DIR = Path("data/hyperliquid/all_trades")

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

# ── Trades ────────────────────────────────────────────────────────────────────

def download_trades():
    s3     = boto3.client("s3")
    bucket = "artemis-hyperliquid-data"

    current = DATE_FROM
    while current <= DATE_TO:
        date_str     = current.strftime("%Y%m%d")
        yyyy, mm, dd = date_str[:4], date_str[4:6], date_str[6:]
        downloaded   = 0

        for hour in range(24):
            hh       = f"{hour:02d}"
            prefix   = f"raw/node_fills/hourly/{yyyy}/{mm}/{dd}/{hh}/"
            out_path = OUTPUT_DIR / date_str / f"{hh}.parquet"

            if out_path.exists():
                downloaded += 1
                continue

            try:
                resp  = s3.list_objects_v2(Bucket=bucket, Prefix=prefix,
                                           RequestPayer="requester")
                files = [obj["Key"] for obj in resp.get("Contents", [])]
            except Exception as e:
                print(f"  {date_str} {hh}:00: {e}")
                continue

            if not files:
                continue

            if s3_download(s3, bucket, files[0], out_path):
                downloaded += 1

        print(f"  {date_str}: {downloaded}/24 файлов")
        current += timedelta(days=1)

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== All Trades (Artemis) ===")
    download_trades()