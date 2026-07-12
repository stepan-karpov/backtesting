"""Реконструкция стакана из инкрементального потока Lighter.

На вход: сообщения order_book — один снепшот `subscribed/order_book` в начале
сбора, дальше дельты `update/order_book` (только изменившиеся уровни, size=0 =
удаление уровня). Сообщения сцеплены по nonce: begin_nonce каждого == nonce
предыдущего, и цепочка непрерывна даже через границу часов.

На выход: по строке-стейту на каждое сообщение — плоская таблица parquet с
метками и top-N уровнями книги.

Чтобы не перечитывать всю историю на каждом запуске, полная книга на конец
последнего обработанного часа хранится в чекпоинте. Он же — источник истины о
том, до какого часа символ уже построен.
"""

import io
import json

import zstandard as zstd
import pandas as pd

from settings import RAW_ROOT, OUT_ROOT, CHANNEL_LOB, LOB_DEPTH, LOB_CHECKPOINT_NAME


def sync():
  """Строит недостающие часы lob для всех символов."""
  symbols = sorted(p.name for p in RAW_ROOT.iterdir() if (p / CHANNEL_LOB).is_dir())
  for symbol in symbols:
    sync_symbol(symbol)


def sync_symbol(symbol):
  """Достраивает символ с того часа, на котором остановился чекпоинт."""
  checkpoint = load_checkpoint(symbol)
  files = hours_to_build(symbol, checkpoint)
  if not files:
    print(f"[lob:{symbol}] актуально, новых часов нет")
    return

  # Стартовое состояние: либо из чекпоинта, либо (первый запуск) из снепшота,
  # который придёт первой строкой первого файла.
  book = {"bids": {}, "asks": {}}
  last_nonce = None
  if checkpoint is not None:
    book = checkpoint["book"]
    last_nonce = checkpoint["last_nonce"]
    print(f"[lob:{symbol}] сид из чекпоинта (конец {checkpoint['last_date']}/{checkpoint['last_hour']}, nonce={last_nonce})")

  for path in files:
    date, hour = date_hour(path)
    last_nonce = build_hour(symbol, path, book, last_nonce)
    save_checkpoint(symbol, book, last_nonce, date, hour)
    print(f"[lob:{symbol}] построен {date}/{hour} -> parquet, чекпоинт обновлён")


def build_hour(symbol, path, book, last_nonce):
  """Обрабатывает один часовой файл: сшивает сообщения в полные стейты и пишет
  parquet. Меняет book на месте, возвращает nonce последнего сообщения."""
  rows = []
  for msg in read_messages(path):
    order_book = msg["order_book"]

    if msg["type"] == "subscribed/order_book":
      # Свежий снепшот (старт сбора или реконнект) — пересобираем книгу с нуля.
      apply_snapshot(book, order_book)
      print(f"[lob:{symbol}] STATE RESET (снепшот) в {path.parent.name}/{path.name}, nonce={order_book['nonce']}")
    else:
      # Дельта продолжает цепочку — состояние обязано быть и метки обязаны сойтись.
      if last_nonce is None:
        raise RuntimeError(f"[lob:{symbol}] дельта без предыдущего состояния в {path.name}: нет ни чекпоинта, ни снепшота")
      if order_book["begin_nonce"] != last_nonce:
        raise RuntimeError(f"[lob:{symbol}] разрыв цепочки в {path.name}: begin_nonce={order_book['begin_nonce']}, ожидался {last_nonce}")
      apply_update(book, order_book)

    last_nonce = order_book["nonce"]
    rows.append(build_row(msg, book))

  write_parquet(symbol, path, rows)
  return last_nonce


# ------------------------- операции над книгой -------------------------

def apply_snapshot(book, order_book):
  """Полностью заменяет книгу содержимым снепшота."""
  book["bids"] = {lvl["price"]: float(lvl["size"]) for lvl in order_book["bids"]}
  book["asks"] = {lvl["price"]: float(lvl["size"]) for lvl in order_book["asks"]}


def apply_update(book, order_book):
  """Применяет дельту: size=0 удаляет уровень, иначе задаёт его новый размер."""
  for side in ("bids", "asks"):
    for lvl in order_book[side]:
      size = float(lvl["size"])
      if size == 0:
        book[side].pop(lvl["price"], None)
      else:
        book[side][lvl["price"]] = size


def build_row(msg, book):
  """Плоская строка-стейт: две метки (мкс) + top-N ask и bid уровней.
  Уровень 1 — лучший; недостающие уровни тонкой книги заполняем нулями."""
  row = {
    "sent_ts": msg["timestamp"] * 1000,   # мс -> мкс
    "recv_ts": msg["receive_timestamp"],  # уже мкс
  }

  asks = top_levels(book["asks"], reverse=False)  # asks по возрастанию цены
  bids = top_levels(book["bids"], reverse=True)   # bids по убыванию цены

  for i in range(LOB_DEPTH):
    px, sz = asks[i] if i < len(asks) else (0.0, 0.0)
    row[f"ask_px_{i + 1}"] = px
    row[f"ask_sz_{i + 1}"] = sz
  for i in range(LOB_DEPTH):
    px, sz = bids[i] if i < len(bids) else (0.0, 0.0)
    row[f"bid_px_{i + 1}"] = px
    row[f"bid_sz_{i + 1}"] = sz

  return row


def top_levels(side, reverse):
  """top-N уровней стороны в виде [(цена, размер)], отсортированных по цене."""
  prices = sorted(side, key=float, reverse=reverse)[:LOB_DEPTH]
  return [(float(price), side[price]) for price in prices]


# ------------------------- ввод/вывод -------------------------

def read_messages(path):
  """Читает .jsonl.zst и отдаёт распарсенные сообщения по одному."""
  with open(path, "rb") as f:
    stream = zstd.ZstdDecompressor().stream_reader(f)
    for line in io.TextIOWrapper(stream, encoding="utf-8"):
      yield json.loads(line)


def write_parquet(symbol, raw_path, rows):
  """Пишет собранные строки-стейты в lighter/SYMBOL/lob/DATE/HH.parquet."""
  date, hour = date_hour(raw_path)
  out_dir = OUT_ROOT / symbol / CHANNEL_LOB / date
  out_dir.mkdir(parents=True, exist_ok=True)
  pd.DataFrame(rows).to_parquet(out_dir / f"{hour}.parquet", compression="zstd")


# ------------------------- чекпоинт -------------------------

def checkpoint_path(symbol):
  return OUT_ROOT / symbol / CHANNEL_LOB / LOB_CHECKPOINT_NAME


def load_checkpoint(symbol):
  """Возвращает чекпоинт символа или None, если его ещё нет."""
  path = checkpoint_path(symbol)
  if not path.exists():
    return None
  with open(path, "rb") as f:
    data = zstd.ZstdDecompressor().decompress(f.read())
  return json.loads(data)


def save_checkpoint(symbol, book, last_nonce, date, hour):
  """Атомарно сохраняет полную книгу и метки на конец обработанного часа."""
  state = {
    "symbol": symbol,
    "last_date": date,
    "last_hour": hour,
    "last_nonce": last_nonce,
    "book": book,
  }
  blob = zstd.ZstdCompressor(level=3).compress(json.dumps(state).encode("utf-8"))

  path = checkpoint_path(symbol)
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(path.name + ".tmp")
  with open(tmp, "wb") as f:
    f.write(blob)
  tmp.replace(path)


# ------------------------- перечень часов -------------------------

def raw_hour_files(symbol):
  """Все часовые файлы lob символа, по возрастанию (дата, час)."""
  channel_dir = RAW_ROOT / symbol / CHANNEL_LOB
  return sorted(channel_dir.rglob("*.jsonl.zst"))


def hours_to_build(symbol, checkpoint):
  """Файлы строго после часа из чекпоинта (или все, если чекпоинта нет)."""
  files = raw_hour_files(symbol)
  if checkpoint is None:
    return files
  last = (checkpoint["last_date"], checkpoint["last_hour"])
  return [f for f in files if date_hour(f) > last]


def date_hour(path):
  """Из .../DATE/HH.jsonl.zst достаёт ('DATE', 'HH')."""
  return path.parent.name, path.name.split(".")[0]
