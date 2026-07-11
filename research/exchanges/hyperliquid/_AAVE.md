# AAVE-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.001
**Цена:** $90.61–$101.08 (диапазон **+11.6% за 5 дней — сильный тренд, как у ZEC**)

AAVE — нативный токен лендингового протокола Aave. В выборке из девяти активов
имеет **уникальный профиль книги**: depth profile почти плоский от L0 к L19
(нет "вакуума" L1 как у SOL/HYPE/ZEC/DOGE), spread редко сидит на 1 tick
(всего 7.28% времени, vs 80% у DOGE). σ/spread = 0.68 — **четвёртый лучший из девяти**,
но spread (1.08 bps) ниже base-tier break-even.

---

## §1 General statistics

- LOB: **778,413** снапшотов, медианный интервал **537 ms** (стандарт)
- Trades: **35,569 taker fills** за 5 дней → **0.08/sec (5/min)** — на уровне DOGE (7), LINK (6)
- Total notional: ~**$4M/день** (215,463 AAVE × $96 / 5 дней) — на уровне TON ($4M), AAVE один из малых рынков
- Mean spread: **10.26 ticks = 1.08 bps** — между ZEC (1.01) и AVAX (0.98)
- Maker fills с rebate: **45.9% count, 63.6% volume** — хорошая top-tier пенетрация

**Тренд:** AAVE сдвинулся $90.61 → $101.08 за 5 дней (+11.6%). Это уровень
ZEC (+11.7%) — данные отражают **трендовый период**, не нейтральный baseline.
σ и микропризнаки могут быть искажены этим bias.

---

## §2 Asset overview

### Spread — **типично выше 1 tick (уникально среди девяти)**

- **Mean 1.08 bps (10.26 ticks)** — между AVAX (8.75 ticks) и ZEC (2.45 ticks)
- p50 = 9, p75 = 14, p90 = 18, p95 = 21, p99 = 31, p99.9 = 58 ticks
- **= 1 tick: только 7.28%** времени — vs DOGE (80%), HYPE (82%), SOL (~10%)
- = 2 ticks: 2.84%
- **≥ 5 ticks: 82.5%** времени — рынок типично **далеко от минимального tick'а**
- **≥ 10 ticks: 49%** — половину времени spread ≥ 10 ticks
- Max 424 ticks (42.5 bps) — экстремальные взрывы
- Skewness +2.74, kurtosis +49 — заметный правый хвост
- **AR(1) = +0.685** — высокая персистентность (между LINK/AVAX 0.67–0.78 и TIA 0.885)

**Уникальная структура:** AAVE — единственный из девяти активов, где spread **не** прилипает
к 1 tick. Мы видим распределение, где типичный spread = 9 ticks, и он сидит там
надолго. Это значит:
1. На L1 нет ожесточённой конкуренции penny-jump'ов (как у HYPE/DOGE)
2. У MM есть место для котирования внутри спреда (1–8 ticks свободно)
3. Penny-jump tactic потенциально работает (улучшить котировку на 1 tick дешево)

### Возвраты
- Stale (Δmid=0): **67.2%** — между ZEC (63%) и DOGE (74%)
- Actual moves: 255,389, std = **0.849 bps**, kurtosis = **+109.8** — fat tails
- p50 move = ? (не указано отдельно), p99 = 22 ticks за 1s горизонт
- σ(1s) = **0.730 bps/s** — между AVAX (0.743) и LINK (0.678)
- σ(5min) = 16.85 bps
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH). Стандарт.

### Signature plot — выраженный momentum

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 0.730 | 0.730 |
| 5s | 1.968 | 0.880 |
| 15s | 3.605 | 0.931 |
| 30s | 5.176 | 0.945 |
| 1min | 7.223 | 0.933 |
| 5min | 16.849 | 0.973 |

σ/√sec растёт с 0.730 до 0.973 — **+33% за 5min**. Это **сильнее momentum чем у ZEC**
(+13%) и DOGE (+22%). Консистентно с +11.6% directional move цены за период.
**Никакого mean reversion** — есть тренд.

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| **SOL** | 0.779 | ~5 | **0.16** ✅ |
| TON | 0.565 | 2.69 | 0.21 ✅ |
| TIA | 0.855 | 3.82 | 0.22 |
| **AAVE** | **0.730** | **1.08** | **0.68** |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| ZEC | 1.341 | 1.01 | 1.33 ❌ |
| HYPE | 0.924 | 0.46 | 2.01 ❌ |
| DOGE | 0.655 | 0.28 | 2.34 ❌❌ |

**AAVE σ/spread = 0.68 — четвёртый лучший из девяти.** Adverse selection
структурно мягче чем у AVAX/LINK (0.76–0.78), значительно лучше HYPE/ZEC/DOGE.
Прохождение half-spread занимает в среднем (0.54/0.73)² ≈ 0.55 секунды —
**рабочее окно** для котировки.

**Для стратегии:** σ/spread достаточно низкий чтобы котирование на best price
не сгорало мгновенно. **Главная проблема — не adverse selection, а абсолютный spread**
(1.08 bps < 3 bps break-even).

---

## §3 Order book structure

### L1 — **тонкая, асимметричная очередь**
- L0: bid **23.45 AAVE ($2,251) / ask 17.76 AAVE ($1,705)** — bid/ask ratio 1.32× (asymmetric)
- Median orders L1: **1 / 1** (mean 1.32 / 1.49) — самая тонкая очередь среди девяти
- Median order size L1: **10.09 / 9.30 AAVE** (~$970 / $893 — крупные ордера)
- p99 = 4 / 5 ордеров, max 19 / 32 — низкая конкуренция (vs HYPE 127, DOGE 61)

**Уникально:** median 1 order на каждой стороне = типично **один большой ордер от
одного участника**. На L1 нет толпы.

### Depth profile — **плоский, без "вакуума"**

| Level | bid_sz | ask_sz | bid_n | ask_n | avg order bid ($) | avg order ask ($) |
|---|---|---|---|---|---|---|
| 0 (best) | 23.45 | 17.76 | 1.32 | 1.49 | 1,709 | 1,142 |
| 1 | 23.79 | 19.50 | 1.31 | 1.42 | 1,738 | 1,316 |
| 2 | 24.32 | 22.68 | 1.35 | 1.40 | 1,736 | 1,554 |
| 5 | 27.70 | 29.52 | 1.39 | 1.41 | 1,916 | 2,010 |
| 10 | 31.41 | 31.91 | 1.42 | 1.43 | 2,129 | 2,141 |
| 19 | 35.12 | 40.90 | 1.35 | 1.39 | 2,499 | 2,820 |

**L0 ≈ L1 ≈ L2** — почти плоский профиль (нет "вакуума" L1 как у SOL/HYPE/DOGE/ZEC).
Слабый постепенный рост к L19. Средний ордер $1,500–2,500 на всех уровнях.

**Интерпретация:** AAVE — рынок, где **каждый MM держит примерно одинаковый ордер
на нескольких уровнях**. Конкуренция размазана по 20 уровням, не сконцентрирована
у L1. Это объясняет почему spread редко на 1 tick — никто не хочет драться за
penny-jump, когда депозиты симметричны.

### Microprice predictiveness — **слабый сигнал**

corr(edge, Δmid_+k) где edge = microprice − mid:
- k=1: **+0.087** (≈ 537 ms)
- k=5: +0.052
- k=10: +0.041
- k=30: +0.024
- k=100: +0.020

Сравнение по девяти активам (corr edge или imbalance в зависимости от источника):
SOL +0.267, DOGE +0.187, AVAX/HYPE +0.157, LINK +0.135, ZEC +0.130, **AAVE +0.087**,
TON +0.059, TIA +0.011.

**AAVE — седьмое место из девяти.** Слабее AVAX/LINK/HYPE. Imbalance несёт мало
информации о ближайшем движении mid — возможно из-за того, что L0/L1 почти
одинаковая глубина (если L1 ≈ L0, imbalance ≠ доминирующий сигнал).

**Для стратегии:** microprice как fair value на AAVE — на грани значимости.
Использовать с малым весом, основной edge должен идти от σ-skew + inventory skew.

---

## §4 Trade analysis

### Масштаб активности
- **35,569 fills за 5 дней = 5/мин** — на уровне DOGE (7), LINK (6), AVAX (8)
- Total: 215,463 AAVE × $96 ≈ **$20.7M / 5 дней = $4.1M/день** — на уровне TON ($4M), один из малых
- В **50× меньше** SOL ($200M), в **8× меньше** ZEC ($31M)

### Структура участников сделок
- Buy 51.8% / Sell 48.2% по count, **47.7% / 52.3% по volume** — sell-aggressor heavier
- Median trade size: **1.52 AAVE** (~$146). Mean: 6.06 AAVE (~$582). p99: 63.4 AAVE (~$6,085)
- Размер крупнее DOGE/HYPE notional, на уровне ZEC

### Multi-leg sweeps
```
Taker legs: 35,569  →  unique events (по time_ms): 22,924  (64.4%)
```
**35.6% legs — части sweep'ов** — между AVAX/LINK (~31%) и DOGE (30%). Не sweep-доминированный.

### Inter-arrival

| Метрика | Значение |
|---|---|
| Mean Δt | 9,338 ms |
| p50 (median) | ~1.7s (estimated) |
| p90 | 40,365 ms (40 s) |
| p99 | 85,651 ms (86 s) |
| Max | 237 s |
| Δt < 50 ms | **35.65%** (бурст-кластеры sweep'ов) |
| Δt > 1 s | 54.4% |
| Δt > 10 s | 30.4% |

Профиль очень похож на DOGE: умеренная активность с burst-кластерами и
длинными паузами. После dedup: λ̂_events ≈ 0.05/sec = **3 уникальных MO/мин**.

**Для стратегии:** ~3 MO/min → 1–2 fills/сторону за 5 минут на L1. Медленный turnover.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, p99 = 620 ms, max gap 405 s — стандарт
- **Trade-to-snapshot lag:** медиана 134 ms, mean 2,758 ms, p99 = 117s — типично

**Для стратегии:** обычные правила. Lag > 2s = не котировать.

---

## §6 Order book microstructure

### Churn — умеренно-высокий
- **Either bid/ask changed: 33.08%** снапшотов — между ZEC (38%) и DOGE (27%)
- Bid changed 24.8%, ask changed 21.1% — лёгкая asymmetry в сторону bid-движений (консистентно с +11.6% тренда вверх)
- **Median L1 lifetime: 0 ms** — L1 меняется быстрее snapshot cadence (как HYPE/ZEC)
- Mean 1,818 ms, p90 4,854 ms

### L1 очередь — минимальная
- Median 1 ордер / сторону — самая тонкая из девяти
- Mean 1.32 bid / 1.49 ask — почти всегда 1–2 ордера
- max 19/32 ордеров — серьёзная конкуренция была лишь в редких пиках

**Для стратегии:** L1 lifetime 0ms означает реальный churn ≥ 1Hz. **Cancel/replace
с латентностью 200ms на каждом snapshot edge.** Queue priority критична —
median 1 ордер значит, что первый поставленный получает весь fill.

---

## §7 Price dynamics

### σ at horizons
- σ(1s) = 0.730 bps, p99 = 2.31 bps
- σ(1min) = 7.34 bps
- σ(5min) = 16.76 bps (160 ticks)

### Range внутри окна
- median Range(1min) = 6.37 bps — за минуту цена проходит ~60 ticks ≈ 6 spreads
- p99 Range(5min) = 46.6 bps — экстремальный диапазон
- median Range(5s) = 0.52 bps — за 5 секунд диапазон ≈ 0.5 spread

**Stale quote horizon:** **~500 ms** = один snapshot. При σ(1s) = 0.730 bps и
half-spread = 0.54 bps (5 ticks), прохождение half-spread в среднем за 550 ms.
Quote должен обновляться **каждый snapshot** (537ms cadence).

---

## §8 Fee economics

- **Effective maker rate: +0.124 bps** — между DOGE (+0.100) и AVAX (+0.190)
- **Effective taker rate: +4.187 bps** — выше среднего
- **Round-trip cost: +4.311 bps**
- Maker fills с rebate: **45.9% count, 63.6% volume** — moderate top-tier penetration
- Avg taker fee: $0.242 USDC

### Базовая экономика для нашей base-tier стратегии

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier (we) | 1.08 bps | 3.0 bps | **−1.92 bps** (минус) |
| Top-tier rebate | 1.08 bps | −0.6 bps | **+1.68 bps** |

**Spread AAVE структурно ниже base-tier break-even на 1.92 bps.** На top-tier rebate
даёт +1.68 bps gross edge — это **больше чем у HYPE (+1.06), DOGE (+0.88), ZEC (+1.61), LINK (+1.47), AVAX (+1.58)**.

### Сравнение top-tier edge × σ/spread (девять активов)

| Актив | Top-tier edge | σ/spread | Volume/день | Качество |
|---|---|---|---|---|
| SOL | +5.6 bps | 0.16 | $200M | ✅✅ |
| TIA | +4.42 bps | 0.22 | small | ✅ |
| TON | +3.29 bps | 0.21 | $4M | ✅ low-volume |
| **AAVE** | **+1.68 bps** | **0.68** | **$4M** | **moderate, low-vol** |
| ZEC | +1.61 bps | 1.33 | $31M | high-vol but hard |
| AVAX | +1.58 bps | 0.76 | $15M | |
| LINK | +1.47 bps | 0.78 | $12M | |
| HYPE | +1.06 bps | 2.01 | $160M | volume saves it |
| DOGE | +0.88 bps | 2.34 | $4M (?) | worst σ/spread |

**AAVE имеет лучший trade-off edge/σ-spread из всего "low-spread" кластера**.
Проблема — низкий объём ($4M/день).

---

## §9 Funding rate — **floor-positive, как у TON/AVAX/LINK**

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:   +0.0821 bps/hr = +1.97 bps/day  (longs PAY shorts)
Std:          0.088 bps/hr  (умеренная)
Min rate:    -0.337 bps/hr  (один глубокий выброс)
Max rate:    +0.125 bps/hr  (capped at floor)
p25/p50/p75: +0.082 / +0.125 / +0.125
Negative rate: 14.2% of hours (низкий)
Mean premium: -3.17 bps (mark < oracle persistently)
```

### Профиль — **стабильный positive funding**

- 85.8% часов rate ≥ 0
- p50 = floor (+0.125 bps/hr) — половину времени на максимуме
- Min -0.337 bps/hr — мягкий негатив, без катастроф (ZEC имел -1.39 bps/hr)
- Премия -3.17 bps — стабильный дисконт perp к oracle, но не глубокий как у SOL (-4.99) или ZEC (-4.99)

### Финансовый эффект для MM

Flow **strongly short-biased** (Open Short $11.1M vs Open Long $8.5M, 56.5% / 43.5% по объёму) →
sell-aggressors доминируют → бьют MM-bid → **MM в лонг**.

При rate +0.082 bps/hr × лонг-инвентарь MM **платит**:
- 50 AAVE long × $96 × 0.082 bps/hr × 24h = **$0.95/день** на $4,800 inventory
- В худший час (-0.337 bps/hr): −$0.16/час = небольшая прибыль для лонга в редких часах

**Для стратегии:** funding cost ~$1/день на $5k капитала — заметно но не катастрофично.
**Аналогично большинству long-biased flow рынков** (ZEC, AVAX, LINK, HYPE).

---

## §10 Market participants

### Концентрация
- **2,085 уникальных адресов** — между TON (1,154) и LINK (2,515)
- **Gini = 0.962** — высокая, стандарт
- Top-5: **32.6%**, Top-20: 69.1%, Top-100: 90.0%

### Top user: 0x8038f0... — pure directional taker
- 1,127 fills, **0% maker**, $3.49M volume, net fee **+$3,251** (заплатил всю taker fee)
- Это **самый большой directional трейдер**, не MM. По объёму равен top-1 на ZEC.

### Реальные pure-maker MM (rebate < 0):

- 0xd071d6d... — 100% maker, $3.15M, **rebate −$32** — топ MM
- 0xf9109ad... — 99.7% maker, $1.95M, **rebate −$56**
- 0x15094c3... — 99.3% maker, $1.73M, **rebate −$49**
- 0xdbcc96b... — 100% maker, $0.46M, **rebate −$56**

**Pure-maker top-tier: 4 видимых стенда $0.5–3M каждый.** Меньше чем у ZEC (3–4 стенда $5–17M),
но больше чем у TON. Конкуренция реальная но не доминирующая.

### Open vs Close flow — **strong short bias**

```
                    n   count_%  volume ($M)  volume_%
Close Long      14,152   19.9%        8.6        20.8%
Close Short     20,004   28.1%       11.0        26.9%
Open Long       14,907   21.0%        8.5        20.8%
Open Short      20,762   29.2%       11.1        27.1%

Open Long:  $8.5M  (43.4%)
Open Short: $11.1M (56.6%)  ← Short в 1.31× больше Long по объёму
```

**Open Short в 1.31× больше Open Long.** Участники в апреле 2026 активно
шортили AAVE — несмотря на то что цена выросла на +11.6%. Это означает:
- Шорты были **wrong** в этот период (ловили падение, которого не было)
- Long-side flow получал прибыль
- MM, занимавший long-side (потому что bid filled), тоже прибыльно

### Open ≈ Close (50.1% / 49.9%) — баланс

---

## Общий сравнительный профиль AAVE

| | SOL | HYPE | ZEC | DOGE | **AAVE** | AVAX | LINK | TON | TIA |
|---|---|---|---|---|---|---|---|---|---|
| Объём/день | $200M | $160M | $31M | small | **$4M** | $15M | $12M | $4M | small |
| Mean spread | 3–8 bps | 0.46 | 1.01 | 0.28 | **1.08** | 0.98 | 0.87 | 2.69 | 3.82 |
| σ(1s) bps | 0.779 | 0.924 | 1.341 | 0.655 | **0.730** | 0.743 | 0.678 | 0.565 | 0.855 |
| σ/spread | 0.16 ✅ | 2.01 | 1.33 | 2.34 | **0.68** | 0.76 | 0.78 | 0.21 | 0.22 |
| Microprice corr | +0.267 | +0.157 | +0.130 | +0.187 | **+0.087** | +0.157 | +0.135 | +0.059 | +0.011 |
| = 1 tick % | ~10% | 82% | — | 80% | **7.3%** ⚡ | — | — | 10% | — |
| Stale % | 84% | 69% | 63% | 74% | **67%** | 60% | 65% | 91% | 84% |
| L1 lifetime (med) | 527 ms | 0 ms | 0 ms | 506 ms | **0 ms** | — | — | 2,672 ms | 1,041 ms |
| Trade rate /min | 50+ | 108 | 18 | 7 | **5** | 8 | 6 | 3 | 2 |
| Funding mean | -0.013 | +0.060 | -0.102 | +0.050 | **+0.082** | +0.101 | +0.109 | +0.117 | -0.097 |
| Flow bias | neutral | long | long | short | **strong short** | long | long | short | small short |
| Maker rebate % vol | 79.5% | 53.5% | 66.5% | 68.4% | **63.6%** | 49.4% | — | 32.4% | 43.6% |
| Eff. maker rate bps | -0.012 | +0.292 | +0.104 | +0.100 | **+0.124** | +0.190 | +0.250 | +0.334 | +0.151 |
| Unique users | 12,390 | 12,616 | 3,681 | 2,668 | **2,085** | 2,542 | 2,515 | 1,154 | 537 |
| Trend (5 days) | mild | mild | **+11.7%** | flat | **+11.6%** | mild | mild | mild | mild |

⚡ = AAVE extreme: spread редко на 1 tick (7.3% vs 80% у DOGE/HYPE).

---

## Ключевые параметры для AS-калибровки (если бы пришлось)

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.730 bps/s | §2 |
| σ/spread ratio | **0.68** — четвёртый лучший из девяти | §2 |
| σ динамика | EWMA halflife 2–3 мин (sample имеет тренд +33% momentum) | §2 |
| Microprice edge | corr = +0.087 — слабый, на грани значимости | §3 |
| L1 median orders | **1 / 1** — тончайшая очередь | §6 |
| Median order size L1 | 10 AAVE = ~$970 | §3 |
| L1 lifetime | **0 ms** median — HYPE-class fast churn | §6 |
| Mean spread | 1.08 bps — **ниже base-tier break-even на 1.92 bps** | §8 |
| Spread regime | типично 5–18 ticks (not pinned to 1) — **уникально** | §2 |
| Top-tier edge | **+1.68 bps gross** — лучший в "low-spread" кластере | §8 |
| Stale quote horizon | ~500 ms = один snapshot | §7 |
| Snapshot cadence | 537 ms median | §5 |
| Funding (Apr 2026) | +0.082 bps/hr mean (mostly floor-pinned) | §9 |
| MM inventory bias | LONG (из-за strong short-biased flow) | §10 |
| Funding эффект для MM | −$1/день на $5k (моden cost) | §9 |
| Expected trade rate | 5/min → ~3 unique MO/мин → 1 fill/сторону / 5 мин | §4 |
| Realistic order size | 1–5 AAVE ($96–480) | §3, §4 |
| Тренд периода | +11.6% за 5 дней — **non-baseline data** | §1 |

---

## Итог: AAVE — лучший σ/spread в low-spread кластере, но низкий объём

### Уникальные черты AAVE

1. **Spread редко на 1 tick (7.3%)** — vs 80% у DOGE/HYPE. AAVE сидит "далеко"
   от минимального tick'а. Penny-jump tactics дёшевы.
2. **Плоский depth profile** — L0 ≈ L1 ≈ L2. Нет "вакуума". Конкуренция
   размазана по 20 уровням, не сконцентрирована у L1.
3. **σ/spread = 0.68** — **четвёртый лучший из девяти.** Структурно мягкая
   adverse selection после SOL/TON/TIA.
4. **Top-tier edge +1.68 bps** — **лучший в low-spread group** (выше AVAX, LINK, ZEC, HYPE, DOGE).
5. **L1 median 1 ордер** — тончайшая очередь. Queue priority критически важна.

### Где AAVE проигрывает остальным "low-spread" кандидатам

1. **Объём $4M/день** — самый низкий в кластере (vs HYPE $160M, ZEC $31M, AVAX $15M).
   Даже при лучшем edge per fill — абсолютный PnL ограничен.
2. **Microprice +0.087** — слабый сигнал, седьмое место из девяти.
3. **Low-confidence sample:** +11.6% движение цены за период означает, что
   σ и σ/spread в trend-режиме. Истинное σ при ranging может быть на 30% ниже,
   что **улучшит** σ/spread до 0.5 — но это нужно валидировать на длинной истории.
4. **Strong short bias в flow** (Open Short 1.31× Open Long) → MM в лонг → платит
   funding (+0.082 bps/hr). Эффект ~$1/день — не критично но негатив.

### Обновлённая рекомендация для нашего старта

С учётом AAVE среди **девяти** активов:

1. ✅ **SOL** — единственный жизнеспособный base-tier. Без вариантов.
2. ⚠️ **HYPE** — priority-2 при top-tier. $160M/день объёма + sweep-богатство.
3. ⚠️ **ZEC** — priority-3 при top-tier. $31M/день + better-than-HYPE σ/spread.
4. ⚠️ **AAVE** — priority-4 при top-tier. **Лучший edge & σ/spread в low-spread кластере**,
   но $4M/день объёма ограничивает absolute PnL.
5. ⚠️ AVAX/LINK — priority-5 (между AAVE и HYPE по объёму, но микропризнаки слабее).
6. ⚠️ DOGE — priority-6 (хороший microprice, но катастрофический σ/spread).
7. ❌ TON / TIA — не жизнеспособны.

**AAVE — кандидат для диверсификации в портфеле 3+ активов.** Если valid SOL и
запускаем HYPE/ZEC по top-tier, AAVE может быть третьим активом: **другой тип рынка**
(трендовый, плоская книга, нет penny-fight за L1), что снижает корреляцию.

### Уникальный риск: trend bias в данных

И ZEC, и AAVE в апреле 2026 двигались **+11–12% за 5 дней**. Это **скоррелированный
тренд**, и калибровать обе стратегии на этом периоде — **двойная экспозиция к одному
рисковому фактору** (rotation в недооценённые DeFi-токены). Перед запуском
обоих нужны данные за нейтральные периоды (>30 дней) для каждого.
