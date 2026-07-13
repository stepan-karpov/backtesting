import asyncio
import json
import logging
import os
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path

import websockets

from settings import DATA_ROOT, SYMBOLS, STREAMS, WS_BASES

SYMBOL_TO_TICKER = {symbol: ticker for ticker, symbol in SYMBOLS.items()}


def setup_info_logger():
  os.makedirs(DATA_ROOT, exist_ok=True)
  logger = logging.getLogger("info_logger")
  logger.setLevel(logging.INFO)

  handler = logging.FileHandler(os.path.join(DATA_ROOT, "binance_raw.log"), encoding="utf-8")
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


def build_stream_url(base):
  """Combined-стрим: все символы × все стримы ЭТОЙ базы в одном соединении.

  Подписка задаётся прямо в URL, поэтому после коннекта мы не отправляем ни
  одного сообщения (лимит на входящие сообщения нас не касается).
  """
  streams = [
    f"{symbol.lower()}@{stream}"
    for symbol in SYMBOLS.values()
    for stream, (_, stream_base) in STREAMS.items()
    if stream_base == base
  ]
  return f"{WS_BASES[base]}?streams={'/'.join(streams)}"


def get_log_path(msg):
  """Маршрутизация по имени стрима из обёртки combined-потока.

  Сообщение приходит как {"stream": "btcusdt@bookTicker", "data": {...}} —
  имени стрима достаточно, внутрь payload'а не заглядываем.
  """
  stream = msg.get("stream", "")
  if "@" not in stream:
    info_logger.warning(f"Message without stream name: {str(msg)[:300]}")
    return None

  symbol, suffix = stream.split("@", 1)

  ticker = SYMBOL_TO_TICKER.get(symbol.upper())
  if not ticker:
    info_logger.warning(f"Unknown symbol: {symbol} (stream: {stream})")
    return None

  if suffix not in STREAMS:
    info_logger.warning(f"Unknown stream type: {suffix} (stream: {stream})")
    return None
  folder = STREAMS[suffix][0]

  now = datetime.now(timezone.utc)
  date_str = now.strftime("%Y%m%d")
  hour_str = now.strftime("%H")

  path = os.path.join(DATA_ROOT, ticker, folder, date_str, f"{hour_str}.jsonl")
  os.makedirs(os.path.dirname(path), exist_ok=True)
  return path


async def connect_and_run(base):
  url = build_stream_url(base)
  info_logger.info(f"[{base}] Attempting to connect to WebSocket...")

  # Binance шлёт ping на уровне протокола раз в 3 минуты — websockets отвечает
  # pong автоматически. Коннект живёт максимум 24 часа, дальше разрыв и
  # переподключение внешним циклом.
  async with websockets.connect(url, max_size=None) as ws:
    info_logger.info(f"[{base}] WebSocket connection established successfully")

    message_count = 0
    total_delay = 0
    count_with_delay = 0

    async for raw in ws:
      msg = json.loads(raw)

      receive_ts = int(time.time() * 1_000_000)
      msg["receive_timestamp"] = receive_ts

      log_path = get_log_path(msg)
      if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
          f.write(json.dumps(msg) + "\n")

      # E — время события на бирже, в миллисекундах.
      event_time = msg.get("data", {}).get("E")
      if event_time:
        total_delay += receive_ts - event_time * 1000
        count_with_delay += 1

      message_count += 1

      # Вывод статистики каждые 1000 сообщений
      if message_count % 1000 == 0 and count_with_delay > 0:
        avg_delay = total_delay / count_with_delay
        size_mb = get_folder_size_mb(DATA_ROOT)

        disk = shutil.disk_usage(DATA_ROOT)
        free_gb = disk.free / (1024 ** 3)

        info_logger.info(
          f"[{base}] Total messages: {message_count} | "
          f"Average delay: {avg_delay:.1f} µs | "
          f"Data size: {size_mb:.2f} MB | "
          f"Free disk: {free_gb:.1f} GB"
        )
        total_delay = 0
        count_with_delay = 0


async def run_base(base):
  """Одно соединение на базу WS, со своим циклом переподключения."""
  while True:
    try:
      await connect_and_run(base)

    except websockets.exceptions.ConnectionClosed as e:
      info_logger.warning(f"[{base}] Connection closed at {datetime.now(timezone.utc)}: {e}")
      info_logger.info(f"[{base}] Reconnecting in 5 seconds...")
      await asyncio.sleep(5)

    except Exception as e:
      info_logger.error(f"[{base}] Unexpected error at {datetime.now(timezone.utc)}: {e}")
      info_logger.info(f"[{base}] Reconnecting in 5 seconds...")
      await asyncio.sleep(5)


async def main():
  # /public и /market — независимые соединения, живут параллельно.
  await asyncio.gather(*(run_base(base) for base in WS_BASES))


if __name__ == "__main__":
  asyncio.run(main())
