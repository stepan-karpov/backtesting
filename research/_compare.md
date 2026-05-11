# Cross-Asset Comparison — 10 Hyperliquid Perps
**Период данных:** Apr 1–5, 2026 (все активы) · LOB + trades
**Break-even base tier:** round-trip 3.0 bps (2 × 0.015% maker)
**Источник:** `research/{ASSET}/DataAnalysis_export/summary.md` каждого актива

Microprice corr = `corr(microprice − mid, Δmid_+1)` из §7.3 при k=1, consistent для всех.
Сортировка по `σ/spread` (adverse selection ratio, от лучшего к худшему).

---

## Основная таблица

| # | Asset | mean_spread_ticks | mean_spread_bps | σ(1s) bps | **σ/spread** | **microprice_corr** | **trades_per_min** | **unique_users** |
|---|---|---|---|---|---|---|---|---|
| 1 | TON | 3.32 | 2.694 | 0.565 | **0.21** | +0.059 | 2.4 | 1,154 |
| 2 | TIA | 11.09 | 3.822 | 0.855 | 0.22 | +0.011 | 2.4 | 537 |
| 3 | AAVE | 10.26 | 1.075 | 0.730 | 0.68 | +0.087 | 4.8 | 2,085 |
| 4 | AVAX | 8.75 | 0.980 | 0.743 | 0.76 | +0.157 | 7.8 | 2,542 |
| 5 | LINK | 7.60 | 0.873 | 0.678 | 0.78 | +0.135 | 6.6 | 2,515 |
| 6 | XPL | 3.49 | 3.088 | 3.574 | 1.16 | +0.162 | 40.2 | 3,480 |
| 7 | ZEC | 2.45 | 1.014 | 1.341 | 1.32 | +0.130 | 18.6 | 3,681 |
| 8 | HYPE | 1.63 | 0.456 | 0.924 | 2.03 | +0.157 | 108.0 | 12,616 |
| 9 | DOGE | 2.55 | 0.279 | 0.655 | 2.35 | +0.187 | 6.6 | 2,668 |
| 10 | SOL | 1.31 | 0.163 | 0.779 | **4.78** | +0.322 | 68.4 | 12,390 |

---

## Распределение метрик по диапазонам

### mean_spread_bps (break-even = 3.0 bps)

- **> 3.0 bps (выше break-even):** TIA (3.82), XPL (3.09)
- **2.0–3.0 bps:** TON (2.69)
- **0.5–2.0 bps:** AAVE (1.08), ZEC (1.01), AVAX (0.98), LINK (0.87)
- **< 0.5 bps:** HYPE (0.46), DOGE (0.28), SOL (0.163)

Разница между крайними значениями: **TIA spread в 23× шире SOL.**

### mean_spread_ticks

- **> 8 ticks:** TIA (11.09), AAVE (10.26), AVAX (8.75)
- **3–8 ticks:** LINK (7.60), XPL (3.49), TON (3.32)
- **1–3 ticks:** DOGE (2.55), ZEC (2.45), HYPE (1.63), SOL (1.31)

Tick precision varies: tick/mid bps ranges from **0.108 bps/tick** (DOGE@$0.092)
до **0.345 bps/tick** (TIA@$0.29).

### σ/spread

- **< 0.5 (рабочий):** TON (0.21), TIA (0.22)
- **0.5–1.0 (граница):** AAVE (0.68), AVAX (0.76), LINK (0.78)
- **1.0–2.0:** XPL (1.16), ZEC (1.32)
- **> 2.0:** HYPE (2.03), DOGE (2.35), SOL (4.78)

Разница между крайними: **SOL σ/spread в 23× хуже TON.**

### microprice_corr (k=1)

- **> 0.2 (сильный):** SOL (+0.322)
- **0.1–0.2 (умеренный):** DOGE (+0.187), XPL (+0.162), AVAX/HYPE (+0.157), LINK (+0.135), ZEC (+0.130)
- **< 0.1 (слабый):** AAVE (+0.087), TON (+0.059), TIA (+0.011)

Разница между крайними: **SOL signal в 29× сильнее TIA.**

### trades_per_min

- **> 30:** HYPE (108), SOL (68), XPL (40)
- **5–30:** ZEC (19), AVAX (8), LINK (7), DOGE (7), AAVE (5)
- **< 5:** TON (2.4), TIA (2.4)

Разница: **HYPE rate в 45× выше TON/TIA.**

### unique_users

- **> 10k:** HYPE (12,616), SOL (12,390)
- **2–5k:** ZEC (3,681), XPL (3,480), DOGE (2,668), AVAX (2,542), LINK (2,515), AAVE (2,085)
- **< 2k:** TON (1,154), TIA (537)

Разница: **HYPE база в 23× шире TIA.**

---

## Top-tier edge (rebate −0.3 bps × 2 = −0.6 bps round-trip cost)

| Asset | Spread (bps) | Top-tier round-trip | Gross edge (bps) |
|---|---|---|---|
| TIA | 3.822 | −0.6 | +4.42 |
| XPL | 3.088 | −0.6 | +3.69 |
| TON | 2.694 | −0.6 | +3.29 |
| AAVE | 1.075 | −0.6 | +1.68 |
| ZEC | 1.014 | −0.6 | +1.61 |
| AVAX | 0.980 | −0.6 | +1.58 |
| LINK | 0.873 | −0.6 | +1.47 |
| HYPE | 0.456 | −0.6 | +1.06 |
| DOGE | 0.279 | −0.6 | +0.88 |
| SOL | 0.163 | −0.6 | +0.76 |

---

## Количественные различия по дополнительным метрикам

| Метрика | Min | Max | Ratio | Min/Max активы |
|---|---|---|---|---|
| Mean spread bps | 0.163 | 3.822 | 23× | SOL / TIA |
| σ(1s) bps | 0.565 | 3.574 | 6.3× | TON / XPL |
| σ/spread | 0.21 | 4.78 | 23× | TON / SOL |
| Microprice corr | +0.011 | +0.322 | 29× | TIA / SOL |
| Trades/min | 2.4 | 108 | 45× | TON,TIA / HYPE |
| Unique users | 537 | 12,616 | 23× | TIA / HYPE |
| Top-tier edge bps | +0.76 | +4.42 | 5.8× | SOL / TIA |

---

## Pareto-границы

Среди 10 активов следующие лежат на Pareto-границе (не доминируются другим
активом по {spread, σ/spread, microprice, trades/min}):

- **TON** — лучший σ/spread (0.21)
- **TIA** — лучший spread (3.82 bps)
- **SOL** — лучший microprice (+0.322), 2-й trades/min (68)
- **HYPE** — лучший trades/min (108)
- **XPL** — единственный с spread > break-even и trades/min > 30

AAVE, AVAX, LINK, ZEC, DOGE — доминируются как минимум одним из Pareto-активов.
