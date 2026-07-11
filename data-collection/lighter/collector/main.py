import asyncio
import json
import logging
import os
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path

import websockets

from settings import MARKETS, DATA_ROOT, CHANNEL_TO_FOLDER

URL = "wss://mainnet.zklighter.elliot.ai/stream"

MARKET_ID_TO_TICKER = {v: k for k, v in MARKETS.items()}

CHANNELS = ["order_book", "ticker", "trade", "market_stats"]


def setup_info_logger():
  os.makedirs(DATA_ROOT, exist_ok=True)
  logger = logging.getLogger("info_logger")
  logger.setLevel(logging.INFO)

  handler = logging.FileHandler(os.path.join(DATA_ROOT, "lighter_raw.log"), encoding="utf-8")
  formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
  )
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  logger.propagate = False
  return logger


info_logger = setup_info_logger()


def get_folder_size_mb(path: str) -> float:
  total_size = 0
  for file_path in Path(path).rglob("*"):
    if file_path.is_file():
      total_size += file_path.stat().st_size
  return total_size / (1024 * 1024)


def get_log_path(msg):
  channel = msg.get("channel", "")
  market_id = None

  if ":" in channel:
    try:
      market_id = int(channel.split(":")[1])
    except (IndexError, ValueError):
      info_logger.warning(f"Failed to parse market_id from message: {str(msg)}")
      return None

  ticker = MARKET_ID_TO_TICKER.get(market_id)
  if not ticker:
    info_logger.warning(f"Unknown market_id: {market_id} (msg: {str(msg)})")
    return None

  folder = CHANNEL_TO_FOLDER.get(channel.split(":")[0])
  if not folder:
    info_logger.warning(f"Unknown channel type: {channel} (msg: {str(msg)})")
    return None

  now = datetime.now(timezone.utc)
  date_str = now.strftime("%Y%m%d")
  hour_str = now.strftime("%H")

  path = os.path.join(DATA_ROOT, ticker, folder, date_str, f"{hour_str}.jsonl")
  os.makedirs(os.path.dirname(path), exist_ok=True)
  return path


async def connect_and_run():
  info_logger.info("Attempting to connect to WebSocket...")

  async with websockets.connect(URL, max_size=None) as ws:
    info_logger.info("WebSocket connection established successfully")

    for name, market_id in MARKETS.items():
      for channel in CHANNELS:
        await ws.send(json.dumps({
          "type": "subscribe",
          "channel": f"{channel}/{market_id}"
        }))

    info_logger.info("All subscriptions sent")

    message_count = 0
    total_delay = 0
    count_with_delay = 0

    async for raw in ws:
      msg = json.loads(raw)

      if msg.get("type", "") == "connected":
        continue

      receive_ts = int(time.time() * 1_000_000)
      msg["receive_timestamp"] = receive_ts

      log_path = get_log_path(msg)
      if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
          f.write(json.dumps(msg) + "\n")

      if "last_updated_at" in msg:
        delay = receive_ts - msg["last_updated_at"]
        total_delay += delay
        count_with_delay += 1

      message_count += 1

      # Вывод статистики каждые 1000 сообщений
      if message_count % 1000 == 0 and count_with_delay > 0:
        avg_delay = total_delay / count_with_delay
        size_mb = get_folder_size_mb(DATA_ROOT)
        
        # Получаем свободное место на диске
        disk = shutil.disk_usage(DATA_ROOT)
        free_gb = disk.free / (1024 ** 3)

        info_logger.info(
          f"Total messages: {message_count} | "
          f"Average delay: {avg_delay:.1f} µs | "
          f"Data size: {size_mb:.2f} MB | "
          f"Free disk: {free_gb:.1f} GB"
        )
        total_delay = 0
        count_with_delay = 0

      if msg.get("type") == "ping":
        await ws.send(json.dumps({"type": "pong"}))


async def main():
  while True:
    try:
      await connect_and_run()

    except websockets.exceptions.ConnectionClosed as e:
      info_logger.warning(f"Connection closed at {datetime.now(timezone.utc)}: {e}")
      info_logger.info("Reconnecting in 5 seconds...")
      await asyncio.sleep(5)

    except Exception as e:
      info_logger.error(f"Unexpected error at {datetime.now(timezone.utc)}: {e}")
      info_logger.info("Reconnecting in 5 seconds...")
      await asyncio.sleep(5)


if __name__ == "__main__":
  asyncio.run(main())