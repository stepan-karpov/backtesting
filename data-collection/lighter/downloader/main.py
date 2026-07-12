import subprocess
from pathlib import Path

# ====================== CONFIG ======================
SSH_KEY     = "/Users/stepan/Desktop/AWS/nodes/asia.pem"
REMOTE_USER = "ubuntu"
REMOTE_HOST = "18.183.168.158"

REMOTE_PATH = "/home/ubuntu/backtesting/data/lighter"
LOCAL_PATH  = "/Users/stepan/Desktop/backtesting/data/lighter-raw"
# ===================================================


def sync_lighter_data():
  # Создаём локальную папку, если её нет
  Path(LOCAL_PATH).mkdir(parents=True, exist_ok=True)

  cmd = [
    "rsync",
    "-avz",
    "--progress",
    # Фильтрация: качаем только сжатые файлы *.jsonl.zst.
    # Порядок правил важен — rsync применяет первое совпавшее:
    "--include", "*/",            # заходим во все подпапки
    "--include", "*.jsonl.zst",   # берём только сжатые jsonl
    "--exclude", "*",             # всё остальное игнорируем
    "--prune-empty-dirs",         # не создаём пустые папки локально
    "-e", f"ssh -i {SSH_KEY}",
    f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}/",
    f"{LOCAL_PATH}/"
  ]

  print(f"Начинаем синхронизацию...")
  print(f"Из: {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}")
  print(f"В:  {LOCAL_PATH}")
  print("-" * 50)

  try:
    subprocess.run(cmd, check=True)
    print("\nСинхронизация успешно завершена.")
  except subprocess.CalledProcessError as e:
    print(f"\nОшибка при синхронизации: {e}")


if __name__ == "__main__":
  sync_lighter_data()