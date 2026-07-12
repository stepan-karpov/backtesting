from settings import CHANNEL_TICKER
from tools.tools import mirror_channel, print_report


def sync() -> None:
  """ticker: каждая строка — полный top-of-book (best bid/ask).

  Самодостаточный стейт → passthrough-зеркало симлинками, без пересчёта.
  """
  stats = mirror_channel(CHANNEL_TICKER)
  print_report(CHANNEL_TICKER, stats)
