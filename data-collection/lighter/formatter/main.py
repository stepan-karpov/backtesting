from settings import OUT_ROOT
from tools import ticker, market_stats, trades, lob

# Каждый модуль знает, как синхронизировать свой канал из lighter-raw в lighter.
# Порядок не важен — каналы независимы.
CHANNELS = [ticker, market_stats, trades, lob]


def main():
  OUT_ROOT.mkdir(parents=True, exist_ok=True)

  print("Синхронизация: lighter-raw -> lighter")
  print("-" * 50)
  for channel in CHANNELS:
    channel.sync()


if __name__ == "__main__":
  main()
