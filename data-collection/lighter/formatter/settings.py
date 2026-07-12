from pathlib import Path

# ====================== ПУТИ ======================
# RAW_ROOT должен совпадать с LOCAL_PATH в downloader/main.py —
# сюда downloader складывает сжатые файлы с удалённой машины.
RAW_ROOT = Path("/Users/stepan/Desktop/backtesting/data/lighter-raw")
# OUT_ROOT — «чистый» датасет, по которому итерируемся.
OUT_ROOT = Path("/Users/stepan/Desktop/backtesting/data/lighter")

# ====================== КАНАЛЫ ======================
# 4 типа данных фиксированы (считаем постоянными).
# ticker / market_stats / trades — каждая строка самодостаточна → passthrough.
# lob — инкрементальный (снепшот + дельты) → отдельная логика (пока stub).
CHANNEL_TICKER = "ticker"
CHANNEL_MARKET_STATS = "market_stats"
CHANNEL_TRADES = "trades"
CHANNEL_LOB = "lob"

# ====================== ПАРАМЕТРЫ LOB ======================
# Глубина книги в выходе: пишем top-N уровней на каждую сторону.
LOB_DEPTH = 30
# Служебный чекпоинт: полная книга + метки на конец последнего обработанного
# часа. По нему определяем, откуда продолжать (см. tools/lob.py).
LOB_CHECKPOINT_NAME = "_state.json.zst"
