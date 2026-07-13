DATA_ROOT = "/data"

# Тикер (как в Lighter, чтобы папки бились между площадками) -> символ перпа
# на Binance USD-M Futures.
#
# Все сверены с fapi/v1/exchangeInfo (contractType=PERPETUAL, status=TRADING,
# quoteAsset=USDT). Числовых префиксов вида 1000X ни у одного нет.
SYMBOLS = {
  # "BTC":      "BTCUSDT",
  "PUMP":     "PUMPUSDT",
  "ADA":      "ADAUSDT",
  "PENGU":    "PENGUUSDT",
  "TIA":      "TIAUSDT",
  "TAO":      "TAOUSDT",
  "SEI":      "SEIUSDT",
  "VIRTUAL":  "VIRTUALUSDT",
}

# Binance разнёс рыночные данные по двум базам (legacy /ws и /stream выведены
# из эксплуатации 2026-04-23):
#   public — высокочастотные данные (bookTicker, depth)
#   market — обычные данные (aggTrade, markPrice, forceOrder, kline, ticker)
# Стрим, подписанный не на свою базу, НЕ отдаёт данных и НЕ выдаёт ошибку —
# просто тишина. Поэтому база указана явно для каждого стрима.
WS_BASES = {
  "public": "wss://fstream.binance.com/public/stream",
  "market": "wss://fstream.binance.com/market/stream",
}

# Суффикс стрима -> (папка на диске, база WS).
# Полный стакан не собираем: BBO per-change (bookTicker) достаточно как ценовой маркер.
STREAMS = {
  "bookTicker":   ("book_ticker",   "public"),  # лучший bid/ask, real-time
  "aggTrade":     ("agg_trades",    "market"),  # сделки, агрегированные по цене и стороне
  "markPrice@1s": ("mark_price",    "market"),  # mark/index price + funding, раз в 1с
  "forceOrder":   ("liquidations",  "market"),  # ликвидации
}
