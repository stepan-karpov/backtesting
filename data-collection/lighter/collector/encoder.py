import os
import logging
from datetime import datetime, timezone
from pathlib import Path

import zstandard as zstd

from settings import DATA_ROOT

def setup_encoder_logger():
  logger = logging.getLogger("encoder")
  logger.setLevel(logging.INFO)

  log_path = os.path.join(DATA_ROOT, "encoder.log")
  handler = logging.FileHandler(log_path, encoding="utf-8")
  formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
  )
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.propagate = False
  return logger


encoder_logger = setup_encoder_logger()


def get_current_active_path():
  now = datetime.now(timezone.utc)
  return now.strftime("%Y%m%d"), now.strftime("%H")


def compress_file(source_path: Path):
  compressed_path = source_path.with_suffix(source_path.suffix + ".zst")
  temp_path = compressed_path.with_suffix(".zst.tmp")

  try:
    cctx = zstd.ZstdCompressor(level=3)

    with open(source_path, "rb") as f_in, open(temp_path, "wb") as f_out:
      cctx.copy_stream(f_in, f_out)

    temp_path.replace(compressed_path)
    source_path.unlink()

    original_size = source_path.stat().st_size if source_path.exists() else 0
    compressed_size = compressed_path.stat().st_size

    encoder_logger.info(
      f"Compressed: {source_path} -> {compressed_path} "
      f"({original_size / 1024 / 1024:.2f} MB -> {compressed_size / 1024 / 1024:.2f} MB)"
    )

  except Exception as e:
    encoder_logger.error(f"Failed to compress {source_path}: {e}")
    if temp_path.exists():
      temp_path.unlink()


def main():
  encoder_logger.info("=== Encoder started ===")

  active_date, active_hour = get_current_active_path()

  for file_path in Path(DATA_ROOT).rglob("*.jsonl"):
    if not file_path.is_file():
      continue

    parts = file_path.parts
    if len(parts) < 4:
      continue

    file_date = parts[-2]
    file_hour = parts[-1].replace(".jsonl", "")

    if file_date == active_date and file_hour == active_hour:
      continue

    compress_file(file_path)

  encoder_logger.info("=== Encoder finished ===")


if __name__ == "__main__":
  main()