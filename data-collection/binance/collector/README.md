Сбор рыночных данных с Binance USD-M Futures.

Собираем 4 стрима на символ (полный стакан НЕ собираем — BBO как ценовой маркер):

| стрим | папка | база WS | что это |
|---|---|---|---|
| `<symbol>@bookTicker` | `book_ticker` | `/public` | лучший bid/ask, real-time |
| `<symbol>@aggTrade` | `agg_trades` | `/market` | сделки, агрегированные по цене и стороне |
| `<symbol>@markPrice@1s` | `mark_price` | `/market` | mark/index price + funding, раз в 1с |
| `<symbol>@forceOrder` | `liquidations` | `/market` | ликвидации |

Раскладка на диске (та же, что у Lighter): `TICKER/<папка>/YYYYMMDD/HH.jsonl(.zst)`.
Тикеры именуются как в Lighter (`BTC`, а не `BTCUSDT`), чтобы папки бились между площадками.

**Два соединения, не одно.** Binance разнёс рыночные данные по двум базам (legacy `/ws`
и `/stream` выведены из эксплуатации 2026-04-23):

- `wss://fstream.binance.com/public/stream` — высокочастотные данные (`bookTicker`, `depth`)
- `wss://fstream.binance.com/market/stream` — обычные данные (`aggTrade`, `markPrice`, `forceOrder`, …)

Стрим, подписанный не на свою базу, **молча не отдаёт данных** — без ошибки и без
дисконнекта. Поэтому база задана явно для каждого стрима в `settings.py`.

```
cd data-collection/binance/collector/

docker build -t binance-collector .

docker run -d \
  --name binance-collector \
  -v ~/backtesting/data/binance:/data \
  -e DATA_ROOT=/data \
  binance-collector
```
