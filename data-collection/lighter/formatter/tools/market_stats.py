from settings import CHANNEL_MARKET_STATS
from tools.tools import mirror_channel, print_report


def sync() -> None:
  """market_stats: каждая строка — полный снимок метрик рынка.

  Самодостаточный стейт → passthrough-зеркало симлинками, без пересчёта.
  """
  stats = mirror_channel(CHANNEL_MARKET_STATS)
  print_report(CHANNEL_MARKET_STATS, stats)
