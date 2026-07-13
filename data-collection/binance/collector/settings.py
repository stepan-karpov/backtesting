DATA_ROOT = "/data"

# Тикер (как в Lighter, чтобы папки бились между площадками) -> символ перпа
# на Binance USD-M Futures.
#
# Все 22 сверены с fapi/v1/exchangeInfo (contractType=PERPETUAL, status=TRADING,
# quoteAsset=USDT). Числовых префиксов вида 1000X ни у одного нет.
SYMBOLS = {
  "BTC":      "BTCUSDT",
  "PUMP":     "PUMPUSDT",
  "ADA":      "ADAUSDT",
  "PENGU":    "PENGUUSDT",
  "TIA":      "TIAUSDT",
  "TAO":      "TAOUSDT",
  "SEI":      "SEIUSDT",
  "VIRTUAL":  "VIRTUALUSDT",
}

# Суффикс стрима -> папка на диске. Полный стакан не собираем: BBO per-change
# (bookTicker) достаточно как ценовой маркер.
STREAM_TO_FOLDER = {
  "bookTicker":   "book_ticker",   # лучший bid/ask, real-time (не throttled)
  "aggTrade":     "agg_trades",    # сделки, агрегированные по цене и стороне
  "markPrice@1s": "mark_price",    # mark/index price + funding rate, раз в 1с
  "forceOrder":   "liquidations",  # ликвидации
}
