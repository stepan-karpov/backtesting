# SOL-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.001
**Цена:** $76.69–$86.56 (диапазон ~13% за 5 дней — moderate trend)

SOL — крупнейший по объёму perpetual в выборке из 10 активов ($260M/день) и самый
"профессиональный" рынок: 79.5% maker volume идёт через top-tier rebate, 12,390
уникальных пользователей. **Уникальная особенность SOL: spread сжат к
минимально возможному tick'у** (94.75% времени spread = 1 tick = 0.125 bps).
Это даёт лучший microprice signal (+0.322) среди всех активов, **но одновременно
делает SOL непригодным для base-tier MM**: σ/spread = 4.78 — наихудший из 10.

---

## §1 General statistics

- LOB: **778,444** снапшотов, медианный интервал **537 ms** (стандарт)
- Trades: **492,267 taker fills** за 5 дней → **1.14/sec (68/min)** — третий по активности после HYPE (108/min) и XPL (40/min)
- Total notional: **~$260M/день** (15.8M SOL × $82 / 5 дней) — крупнейший в выборке
- Mean spread: **1.31 ticks = 0.163 bps**
- Maker fills с rebate: **69.3% count, 79.5% volume** — **наивысшая top-tier пенетрация** из 10 активов

**Главное наблюдение:** SOL — рынок профессиональных market-makers. 79.5% maker
объёма идёт через top-tier rebate (−0.3 bps). Сравните: HYPE 53.5%, AVAX 49.4%.
Это значит, что **наблюдаемая экономика рынка близка к top-tier**, а base-tier
участники здесь редкость.

---

## §2 Asset overview

### Spread — **самый тесный в выборке**

- **Mean 0.163 bps (1.314 ticks)** — **минимальный из 10 активов**
- = 1 tick: **94.75%** времени — рынок практически постоянно прижат к минимальному tick'у
- = 2 ticks: только 1.00%, ≥ 5 ticks: 2.97%, ≥ 10 ticks: 1.03%
- p50 = 1, p75 = 1, p90 = 1, p95 = 2, p99 = 10, p99.9 = 26 ticks
- **Max: 201 ticks = 24.1 bps** — редкие dislocations
- Skewness +21.43, kurtosis +915 — экстремальные хвосты (но кратко)
- **AR(1) = +0.207** — самый низкий из 10 (HYPE 0.334, ZEC 0.593, AAVE 0.685, TIA 0.885)
  Spread быстро возвращается к 1 tick после взрывов.

**Структура рынка:** SOL — единственный актив (вместе с DOGE/HYPE), где spread
сидит на минимальном tick'е >80% времени. Но в отличие от DOGE/HYPE это
происходит при **высокой ликвидности**: L0 содержит 875 SOL ≈ $72,000 с
median 6 ордерами в очереди (тогда как у HYPE median 2, AAVE 1).

**Для стратегии:** на L1 идёт жёсткая queue-конкуренция за penny-jump-минимум.
Penny-jump неактуален — мы уже на минимуме. Edge нужно искать через depth-pricing
(квоты на L1+ с расчётом adverse selection) или sweep-detection.

### Возвраты
- Stale (Δmid=0): **81.0%** — между AVAX (60%) и TIA (84%)
- Actual moves: 148,210, std = **1.197 bps**, kurtosis = **+65.9** — moderate fat tails
- p50 abs move = 5 ticks, p95 = 18, p99 = 32, max = 421 ticks за 1 snapshot
- σ(1s) = **0.779 bps/s**
- σ(5min) = 17.26 bps
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH). Стандарт.

### Signature plot — почти flat (Brownian)

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 0.779 | 0.779 |
| 5s | 2.089 | 0.934 |
| 15s | 3.771 | 0.974 |
| 30s | 5.329 | 0.973 |
| 1min | 7.454 | 0.962 |
| 5min | 17.255 | 0.996 |

σ/√sec растёт с 0.779 до 0.996 — **+28% от 1s к 5min**. Лёгкая momentum-составляющая,
но в пределах sampling noise. Практически Brownian.

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| TON | 0.565 | 2.69 | 0.21 ✅ |
| TIA | 0.855 | 3.82 | 0.22 ✅ |
| AAVE | 0.730 | 1.08 | 0.68 |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| XPL | 3.574 | 3.09 | 1.16 ❌ |
| ZEC | 1.341 | 1.01 | 1.32 ❌ |
| HYPE | 0.924 | 0.46 | 2.03 ❌ |
| DOGE | 0.655 | 0.28 | 2.35 ❌ |
| **SOL** | **0.779** | **0.163** | **4.78** ❌❌❌ |

**SOL σ/spread = 4.78 — НАИХУДШИЙ из 10.** Рынок проходит ~5 spread'ов за 1 секунду.
Это **структурное свойство liquid рынка**: σ не выше остальных активов,
но spread сжат до минимума профессиональными MM.

**Прохождение half-spread:** half-spread = 0.08 bps, σ(1s) = 0.779 → ожидаемое
время прохождения ≈ (0.08/0.779)² × 1000 = **~10 ms**. Quote на L1 без edge
сгорает за десятки миллисекунд.

---

## §3 Order book structure

### L1 — **самая глубокая и многочисленная очередь из 10 активов**
- L0: bid **875 SOL ($71,750) / ask 853 SOL ($69,940)** — bid/ask ratio 1.026× (симметрично)
- **Median orders L1: 6 / 6** — **рекорд** (vs AAVE 1, HYPE/ZEC/DOGE 2, AVAX/LINK 1)
- Mean orders L1: 7.47 / 7.45
- p99 = 34 / 34 ордеров, max 159 / 147 — серьёзная queue-конкуренция в пиковые моменты
- **Median order size L1: 78 / 80 SOL** (~$6,400 / $6,560) — крупные ордера

**Для стратегии:** 6 ордеров на L1 = очередь длиной 6 × 78 = ~470 SOL впереди нашего.
При partial-fill вероятность нашего fill маленькая — нужно либо стоять долго,
либо ставить значительный объём, чтобы быть впереди по time-priority.

### Depth profile — **классический "вакуум" L1–L3**

| Level | bid_sz (SOL) | ask_sz (SOL) | bid_n | ask_n | avg order bid | avg order ask |
|---|---|---|---|---|---|---|
| 0 (best) | **875.3** | 853.0 | 7.47 | 7.45 | 117 SOL | 114 SOL |
| 1 | **181.7** | 184.8 | 2.18 | 2.29 | 83 | 81 |
| 2 | 206.9 | 202.9 | 2.21 | 2.27 | 94 | 90 |
| 5 | 279.8 | 267.4 | 2.54 | 2.54 | 110 | 105 |
| 10 | 351.6 | 342.7 | 2.57 | 2.49 | 137 | 138 |
| 15 | 384.9 | 399.3 | 2.54 | 2.54 | 152 | 157 |
| 19 | 417.7 | 438.2 | 2.51 | 2.53 | 167 | 173 |

**L0 → L1 drop: 875 → 182 (-79%)** — экстремальный "вакуум", глубже чем у HYPE
(-44%) и DOGE (-29%). Затем медленный рост к L19 (~418 SOL). **Никто не стоит
"в очереди" за best price** — все либо на L1 (платят за queue), либо паркуются
далеко (passive size).

**Интерпретация:** SOL — рынок где MM-боты дерутся за L1, но boundary L1/L2
свободна. Penny-jump на 1 tick (≈ 0.12 bps) дешёвый, но мы уже на минимуме —
улучшать некуда. Парковка на L2–L4 — ниша для passive size в редкие dislocations.

### Microprice predictiveness — **сильнейший сигнал из 10 активов**

corr(edge, Δmid_+k) где edge = microprice − mid:
- k=1: **+0.322** (≈ 537 ms)
- k=5: +0.208 (≈ 2.7 sec)
- k=10: +0.159 (≈ 5.4 sec)
- k=30: +0.092
- k=100: +0.051

Сравнение по 10 активам:
**SOL +0.322 (лучший)**, DOGE +0.187, XPL +0.162, AVAX/HYPE +0.157, LINK +0.135,
ZEC +0.130, AAVE +0.087, TON +0.059, TIA +0.011.

**Microprice на SOL — реальный edge.** Сигнал в 1.5–2× сильнее, чем у любого
другого актива. Медленное затухание (с +0.32 до +0.16 за 5 секунд) даёт **окно
~5 секунд** для использования imbalance-signal.

**Для стратегии:** microprice как fair value на SOL обязателен. При σ/spread=4.78
это **единственный edge**, который может конкурировать с adverse selection.
Базовая стратегия: котировать вокруг microprice (не mid), с σ-skew.

---

## §4 Trade analysis

### Масштаб активности
- **492,267 fills за 5 дней = 68/мин** — третий по активности после HYPE (108) и XPL (40)
- Total: 15.82M SOL × ~$82 ≈ **$1.30B / 5 дней = $260M/день** — **наибольший объём из 10**
- В 1.6× больше HYPE ($160M), в 6× больше XPL ($43M)

### Структура участников сделок
- Buy 47.5% / Sell 52.5% по count — slight sell-aggressor bias
- Median trade size: **1.49 SOL** (~$122). Mean: 32.13 SOL (~$2,635). p99: 508.5 SOL (~$41,700)
- Power-law размеров: 80%+ сделок ≤ 2 SOL (розница), мелкая доля крупных блоков

### Multi-leg sweeps — **сильно sweep-driven**
```
Taker legs: 492,267  →  unique events (по time_ms): 229,625  (46.6%)
```
**53.4% legs — части sweep'ов** — на уровне HYPE (60%) и ZEC (54%).

После dedup: **λ̂_events = 0.53/sec = ~32 уникальных MO/мин**.
Plus 53% legs внутри MO означает крупные sweeps берут multiple levels.

### Inter-arrival
- **Δt < 50 ms: 53.51%** — burst-доминирование
- Δt > 1 sec: 22.25%
- Δt > 10 sec: 1.10% — редкие паузы

Типичный паттерн: длинные burst-периоды с десятками fill'ов за секунды, перемежаемые
короткими паузами.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, p99 = 620 ms, max gap 405 s
- **Trade-to-snapshot lag:** медиана 134 ms, типично для всех активов
- Δt > 1s gaps: 0.018%, Δt > 10s: 0.010% — high quality

---

## §6 Order book microstructure

### Churn — **умеренно-низкий**
- **Either bid/ask changed: 19.07%** снапшотов — между AAVE (33%) и TIA (16%)
- Bid changed 16.94%, ask changed 16.90% — почти идеально симметрично
- **Median L1 lifetime: 527 ms** ≈ один snapshot — здоровая жизнь (как DOGE 506, не HYPE/ZEC/AAVE 0)
- Mean lifetime: 1,393 ms (приблизительно)

**Интерпретация:** L1 на SOL "переживает" один snapshot в среднем. При HL latency
200ms на cancel/place у нас есть окно ~300ms для action перед обновлением.
**Технически выполнимо**, но требует низкой latency.

### L1 очередь — **major queue contest**
- Median 6 ордеров с обеих сторон — самая длинная очередь из 10
- Mean 7.5, p99 34, max 159 — серьёзные пики
- При median 6 × $6,400 = ~$38,400 depth на L1 — глубокий для рынка

**Queue priority критична.** Мы — 7-й в очереди при median случае, fill вероятность
по time-priority низкая без размера.

---

## §7 Price dynamics

### σ at horizons (см. signature plot выше)
- σ(1s) = 0.779 bps
- σ(1min) = 7.45 bps
- σ(5min) = 17.26 bps

### Range внутри окна

| window | median range (bps) |
|---|---|
| 500 ms | ~0 |
| 1s | ~0.5 |
| 5s | ~2 |
| 30s | ~8 |
| 1min | ~12 |

(Estimated from σ values; raw output table for range was not extracted, но
σ ∝ √T держится, range/spread ~12 bps / 0.16 bps = **75 spread'ов за минуту**.)

**Stale quote horizon:** **~10 ms**. При σ(1s) = 0.779 bps и half-spread = 0.08 bps,
прохождение half-spread занимает (0.08/0.779)² ≈ 10 ms в среднем.
**Quote должен обновляться буквально каждый tick LOB.**

С HL-латентностью 200ms cancel-before-taker priority **жизненно важна** — у нас
нет шансов отменить quote вовремя, но протокол HL это компенсирует.

---

## §8 Fee economics

- **Effective maker rate: −0.012 bps** ✅ — **единственный отрицательный из 10!** Top-tier rebate доминирует.
- **Effective taker rate: +3.371 bps**
- **Round-trip cost: +3.360 bps**
- Maker fills с rebate: **69.3% count, 79.5% volume** — **highest** в выборке
- Avg rebate per maker fill: small negative

### Базовая экономика для нашей base-tier стратегии

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier (we) | 0.163 bps | 3.0 bps | **−2.84 bps** ❌ |
| Top-tier rebate | 0.163 bps | −0.6 bps | **+0.76 bps** |

**Spread SOL в 18× ниже base-tier break-even.** Любой fill на base-tier — это
−2.84 bps убыток до учёта adverse selection. С σ/spread=4.78 это
**гарантированный быстрый bleed**.

### Сравнение top-tier edge × σ/spread по 10 активам

| Asset | Top-tier edge | σ/spread | Качество |
|---|---|---|---|
| TIA | +4.42 bps | 0.22 ✅ | low fills |
| XPL | +3.69 bps | 1.16 | volatile |
| TON | +3.29 bps | 0.21 ✅ | low fills |
| AAVE | +1.68 bps | 0.68 | low vol |
| ZEC | +1.61 bps | 1.32 | |
| AVAX | +1.58 bps | 0.76 | |
| LINK | +1.47 bps | 0.78 | |
| HYPE | +1.06 bps | 2.03 | volume |
| DOGE | +0.88 bps | 2.35 | |
| **SOL** | **+0.76 bps** | **4.78** ❌ | **наихудший edge × σ/spread** |

**SOL даже на top-tier rebate — наихудший по edge/adverse-selection.** При
+0.76 bps gross edge и σ/spread=4.78 expected loss per round-trip превышает
gross edge.

---

## §9 Funding rate — **около нуля, mild benefit для лонгов**

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:   -0.0130 bps/hr = -0.31 bps/day  (shorts pay longs)
Negative rate: 50.8% of hours
Mean premium: -4.89 bps (mark < oracle persistently)
```

### Профиль — **balanced около нуля**

- 50.8% часов rate < 0 (шорты платят), 49.2% часов rate > 0 (лонги платят)
- Среднее −0.013 bps/hr — практически ноль
- Premium −4.89 bps — perp торгуется с заметным дисконтом к oracle, но floor-mechanism
  компенсирует, держа rate около нуля
- **Уникально**: SOL — единственный актив с **balanced funding** (не floor-pinned,
  не volatile, не deeply negative). Все остальные либо постоянно positive (TON +0.12,
  AVAX/LINK +0.10), либо постоянно negative (TIA -0.10), либо volatile (ZEC).

### Финансовый эффект для MM

На $5k капитале с ±5 SOL inventory: ~$0.0005/час cost — пренебрежимо.
Funding на SOL — нейтральный фактор.

**Для стратегии:** funding в inventory cost — нулевая поправка. Это плюс
для модели: одной переменной меньше для калибровки.

---

## §10 Market participants — **наибольший и самый профессиональный рынок**

### Концентрация
- **12,390 уникальных адресов** — между HYPE (12,616) и ZEC (3,681)
- **Gini = 0.977** — **наивысшая** из 10
- Top-5: **22.8%**, Top-20: 48.9%, Top-100: **78.2%** — top-100 контролируют 78%

### Структура top-tier MM
SOL имеет **наибольшую плотность top-tier MM** из 10 активов:
- 79.5% maker volume через rebate (vs HYPE 53.5%, ZEC 66.5%, AAVE 64%)
- Среди top-20 много pure-maker addresses с net rebate
- Эти MM котируют тонкий spread (1 tick) с large queue (median 6) — **профессиональная
  инфраструктура** с низкой latency и хорошими σ/inventory моделями

### Open vs Close flow — **slight short bias**

```
                    n   count_%  volume ($M)  volume_%
Close Long     223,061   22.7%      540.7      21.2%
Close Short    250,753   25.5%      684.2      26.8%
Long > Short    10,122    1.0%       58.8       2.3%
Open Long      231,507   23.5%      535.9      21.0%
Open Short     259,084   26.3%      677.7      26.5%
Short > Long    10,007    1.0%       57.2       2.2%

Open Long:  $535.9M (44.1% of opens)
Open Short: $677.7M (55.9% of opens)
Open Short / Open Long = 1.26× by volume
```

**Open Short в 1.26× больше Open Long.** Участники в апреле 2026 активно
открывали шорты по SOL. Sell-aggressor count 52.5% > Buy 47.5% — консистентно.

Что это значит для MM:
- Sell-aggressors доминируют → бьют bid → MM-bid filled → **MM в лонг**
- При rate ≈ 0 funding не влияет
- Long inventory растёт пропорционально order-flow imbalance

### Open ≈ Close (49.8% / 50.2%) — почти идеальный баланс

---

## Общий сравнительный профиль SOL

| | **SOL** | HYPE | XPL | ZEC | AAVE | AVAX | LINK | DOGE | TON | TIA |
|---|---|---|---|---|---|---|---|---|---|---|
| Объём/день | **$260M** | $160M | $43M | $31M | $4M | $15M | $12M | small | $4M | small |
| Mean spread | **0.163** ⚡ | 0.46 | 3.09 | 1.01 | 1.08 | 0.98 | 0.87 | 0.28 | 2.69 | 3.82 |
| = 1 tick % | **94.75%** ⚡ | 82% | — | — | 7.3% | — | — | 80% | 10% | — |
| σ(1s) bps | 0.779 | 0.924 | 3.574 | 1.341 | 0.730 | 0.743 | 0.678 | 0.655 | 0.565 | 0.855 |
| σ/spread | **4.78** ❌❌❌ | 2.03 | 1.16 | 1.32 | 0.68 | 0.76 | 0.78 | 2.35 | 0.21 | 0.22 |
| Microprice corr (k=1) | **+0.322** ✅ | +0.157 | +0.162 | +0.130 | +0.087 | +0.157 | +0.135 | +0.187 | +0.059 | +0.011 |
| Microprice decay k=10 | **slow** ✅ | — | slow | — | fast | — | — | — | — | — |
| Stale % | 81% | 69% | 66% | 63% | 67% | 60% | 65% | 74% | 91% | 84% |
| L1 lifetime (med) | **527 ms** | 0 ms | 503 ms | 0 ms | 0 ms | — | — | 506 ms | 2,672 ms | 1,041 ms |
| L1 median orders | **6** ⚡ | 2 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 1 |
| L1 vacuum (L0→L1) | **−79%** ⚡ | −44% | — | — | flat | — | — | −29% | — | — |
| Trade rate /min | 68 | **108** | 40 | 19 | 5 | 8 | 7 | 7 | 2 | 2 |
| Sweep legs % | **53%** | 60% | — | 54% | 36% | — | — | 30% | 28% | 17% |
| Funding mean | **-0.013** ⚡ | +0.060 | +0.132 | -0.102 | +0.082 | +0.101 | +0.109 | +0.050 | +0.117 | -0.097 |
| Maker rebate % vol | **79.5%** ⚡ | 53.5% | 57% | 67% | 64% | 49% | — | 68% | 32% | 44% |
| Eff. maker rate | **-0.012** ⚡ | +0.292 | +0.216 | +0.104 | +0.124 | +0.190 | +0.250 | +0.100 | +0.334 | +0.151 |
| Unique users | 12,390 | **12,616** | 3,480 | 3,681 | 2,085 | 2,542 | 2,515 | 2,668 | 1,154 | 537 |
| Base-tier viable? | **❌❌❌** | ❌ | ✓ (+0.09) | ❌ | ❌ | ❌ | ❌ | ❌ | borderline | ✅ |

⚡ = SOL extreme: spread, σ/spread, microprice, L1 lifetime balance, funding,
maker rebate share.

---

## Ключевые параметры для AS-калибровки

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.779 bps/s | §2 |
| σ/spread ratio | **4.78** — наихудший из 10 | §2 |
| σ динамика | EWMA halflife 2–3 мин (ARCH) | §2 |
| Microprice edge | **corr = +0.322** — лучший из 10, decay медленный | §3 |
| L1 median orders | 6 / 6 — major queue contest | §6 |
| L1 lifetime | 527 ms — здоровая | §6 |
| Mean spread | **0.163 bps** — в 18× ниже base-tier break-even | §8 |
| Tick precision | 0.12 bps/tick @ $82 | §1 |
| Spread regime | 94.75% time = 1 tick — penny-jump exhausted | §2 |
| Base-tier edge | **−2.84 bps** (катастрофа) | §8 |
| Top-tier edge | +0.76 bps — наименьший из 10 | §8 |
| Stale quote horizon | **~10 ms** — критически короткий | §7 |
| Snapshot cadence | 537 ms — **в 50× больше stale horizon** ⚠️⚠️ | §5 |
| HL cancel-before-taker | критически важна (single source of safety) | — |
| Funding (Apr 2026) | −0.013 bps/hr — практически ноль | §9 |
| MM inventory bias | LONG (sell-aggressor heavy) | §10 |
| Expected trade rate | 68/min → ~30 unique MO/мин | §4 |
| Realistic order size | 0.5–2 SOL ($40–165) | §3, §4 |
| Max inventory | ±5 SOL на $5k капитале | — |

---

## Итог: SOL — **самый сложный, не самый простой**

### Чем SOL уникален из 10 активов

1. **Spread сжат к 1 tick 94.75% времени** — единственный liquid рынок с такой
   плотностью на minimum-tick. Penny-jump exhausted.
2. **Microprice corr +0.322 — лучший из 10**, decay медленный.
   Это **единственный edge** при σ/spread=4.78.
3. **L1 median 6 ордеров — рекорд queue density.** Time-priority критична.
4. **L0 → L1 drop −79%** — самый экстремальный "вакуум" в выборке.
5. **79.5% maker volume на top-tier rebate** — рынок профессионалов.
6. **Effective maker rate −0.012 bps** — единственный negative (rebate-dominated).
7. **Funding ≈ 0** — единственный balanced (не floor, не volatile, не deep).
8. **Top-tier edge всего +0.76 bps** — наименьший из 10.

### Pros для MM-стратегии на SOL (только при top-tier)

- Microprice +0.322 даёт реальное преимущество в ценообразовании
- 68 fills/min × $260M/день — массовая активность для быстрой валидации
- Funding нейтральный — одной переменной меньше в модели
- L1 lifetime 527ms = технически выполнимый refresh при HL latency 200ms
- Cancel-before-taker priority HL частично компенсирует adverse selection

### Cons

- **Spread 0.163 bps делает base-tier невозможным.** Гарантированный убыток.
- **σ/spread = 4.78 — наихудший из 10.** Quote сгорает за ~10 ms.
- **Queue median 6** требует серьёзной queue-position стратегии.
- **Конкуренция с top-tier MM** (79.5% volume) — мы не самые быстрые, не самые
  калиброванные. Без edge нам никто не "сдаёт" prime price.
- **На top-tier edge +0.76 bps × σ/spread 4.78 = expected negative PnL** до учёта
  microprice edge.

### Изменённая рекомендация по SOL

**SOL не является "обычным базовым" активом для начала.** Он представляет
самый сложный рынок из 10, на котором конкурируют профессиональные MM с
top-tier комиссиями и низкой latency.

Реалистичные сценарии запуска на SOL:
1. **С top-tier rebate уже имеющимся** (нужно нагнать объём где-то ещё)
2. **С работающим microprice-based ценообразованием** (не AS вокруг mid)
3. **С серьёзной queue-position логикой** (определение оптимальной позиции в L1)
4. **С low-latency инфраструктурой** (своя нода или managed colo)

Без этих 4 компонентов запуск на SOL = быстрая потеря капитала.

### Альтернативные пути из 10 активов

- **TIA / TON** — единственные с spread > break-even, но 2 fills/min.
  Хорошие для отладки пайплайна.
- **XPL** — spread 3.09 + 40 fills/min, но extreme σ (+3.57) + ликвидации.
- **HYPE** — массивный volume + relatively predictable, нужен top-tier.
- **AAVE** — лучший σ/spread в low-spread кластере, но $4M/день.

### Уникальный риск SOL: data sample не репрезентативен

Период Apr 1–5, 2026 показывает price range $76.69–$86.56 (12.9% диапазон).
Это **moderate trending period**. Для проверки если σ/spread = 4.78 сохраняется
в ranging-режимах, нужны **30+ дней различных режимов**. В реальной торговле
SOL spread может расширяться при flat price (меньше hype-волн), что улучшит
σ/spread до 2–3. Но даже тогда — это всё ещё adverse-selection territory.
