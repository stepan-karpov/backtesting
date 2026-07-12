from settings import CHANNEL_TRADES
from tools.tools import mirror_channel, print_report


def sync() -> None:
  """trades: каждая строка — батч случившихся сделок (события, самодостаточны).

  Разворачивать нечего → passthrough-зеркало симлинками.
  """
  stats = mirror_channel(CHANNEL_TRADES)
  print_report(CHANNEL_TRADES, stats)
