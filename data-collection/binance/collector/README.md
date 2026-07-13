Сбор рыночных данных с Binance USD-M Futures.

Собираем 4 стрима на символ (полный стакан НЕ собираем — BBO как ценовой маркер):

| стрим | папка | что это |
|---|---|---|
| `<symbol>@bookTicker` | `book_ticker` | лучший bid/ask, real-time |
| `<symbol>@aggTrade` | `agg_trades` | сделки, агрегированные по цене и стороне |
| `<symbol>@markPrice@1s` | `mark_price` | mark/index price + funding, раз в 1с |
| `<symbol>@forceOrder` | `liquidations` | ликвидации |

Раскладка на диске (та же, что у Lighter): `TICKER/<папка>/YYYYMMDD/HH.jsonl(.zst)`.
Тикеры именуются как в Lighter (`BTC`, а не `BTCUSDT`), чтобы папки бились между площадками.

Все стримы идут одним combined-соединением: `wss://fstream.binance.com/public/stream?streams=...`
(legacy `/ws` и `/stream` выведены из эксплуатации 2026-04-23).

```
cd data-collection/binance/collector/

docker build -t binance-collector .

docker run -d \
  --name binance-collector \
  -v ~/backtesting/data/binance:/data \
  -e DATA_ROOT=/data \
  binance-collector
```
