import os
from collections import Counter
from pathlib import Path

from settings import RAW_ROOT, OUT_ROOT


def ensure_relative_symlink(raw_file: Path) -> str:
  """Гарантирует, что OUT_ROOT/<rel> — корректный относительный симлинк на raw_file.

  Относительный путь (а не абсолютный) — чтобы ссылки переживали перемещение
  всей папки data/ целиком.

  Возвращает статус:
    "created"  — симлинка не было, создали;
    "skipped"  — уже есть и указывает куда надо;
    "relinked" — был симлинк, но битый/не туда — пересоздали;
    "conflict" — на месте реальный файл (не наш случай), не трогаем.
  """
  rel = raw_file.relative_to(RAW_ROOT)
  out_file = OUT_ROOT / rel
  out_file.parent.mkdir(parents=True, exist_ok=True)

  target = os.path.relpath(raw_file, out_file.parent)

  if out_file.is_symlink():
    if os.readlink(out_file) == target:
      return "skipped"
    out_file.unlink()
    os.symlink(target, out_file)
    return "relinked"

  if out_file.exists():
    return "conflict"

  os.symlink(target, out_file)
  return "created"


def mirror_channel(channel: str) -> Counter:
  """Досоздаёт недостающие симлинки для всех SYMBOL/<channel>/**/*.jsonl.zst.

  Инкрементально и идемпотентно: правило «нет в выходе → создать». Опирается на
  то, что скачанные .jsonl.zst неизменяемы, поэтому уже существующие не трогаем.
  """
  stats = Counter()
  for symbol_dir in sorted(RAW_ROOT.iterdir()):
    if not symbol_dir.is_dir():
      continue

    channel_dir = symbol_dir / channel
    if not channel_dir.is_dir():
      continue

    for raw_file in sorted(channel_dir.rglob("*.jsonl.zst")):
      if raw_file.is_file():
        stats[ensure_relative_symlink(raw_file)] += 1

  return stats


def print_report(channel: str, stats: Counter) -> None:
  line = (
    f"[{channel}] создано {stats['created']}, "
    f"пересоздано {stats['relinked']}, пропущено {stats['skipped']}"
  )
  if stats["conflict"]:
    line += f", КОНФЛИКТ {stats['conflict']}"
  print(line)
