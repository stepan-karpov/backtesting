# DOGE-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.000001
**Цена:** $0.0923 (диапазон ~50 bps за 5 дней — самый стабильный актив выборки)

DOGE — оригинальный мемкойн ($0.09, market cap ~$13B). В нашей выборке из семи
активов это **актив с самым тесным спредом** (0.28 bps mean, 79.8% времени = 1 tick).
Комбинация tight spread + умеренный σ даёт **наихудший σ/spread = 2.34**, делая
DOGE структурно непригодным для base-tier MM. Профиль ближе всего к HYPE и ZEC:
"тесный spread + adverse selection burn", но с заметно меньшим объёмом ($10M/день).

---

## §1 General statistics

- LOB: **778,473** снапшотов, медианный интервал **537 ms** (стандарт)
- Trades: **46,285 taker fills** за 5 дней → **0.11/sec (6.6/min)** — между TON (3/min) и ZEC (18/min)
- Total notional: **~$10–11M/день** (295M DOGE × $0.092 / 5 дней) — между LINK ($12M) и TON ($4M)
- Mean spread: **2.55 ticks = 0.28 bps** — **тестейший из семи**
- Maker fills с rebate: **60.9% count, 68.4% volume** — хорошее top-tier penetration

**Уникальная находка:** при цене $0.092276 один tick = $0.000001 = **0.108 bps**.
Это самый "тонкий" tick relative to price среди всех изученных активов
(SOL ~0.1 bps tick, HYPE 0.28 bps tick, ZEC 0.4 bps tick). На цене $0.09 биржа
выдаёт 6 значащих цифр precision — больше нет инструмента "копнуть глубже".

---

## §2 Asset overview

### Spread — **биполярное распределение**

- **Mean 0.28 bps (2.55 ticks)** — но это среднее обмануто хвостом
- **= 1 tick: 79.83% времени** — четыре пятых времени spread на абсолютном минимуме
- = 2 ticks: только **1.56%** (!) — спред почти не сидит на 2 ticks, скачет через
- ≥ 5 ticks: 15.4%, ≥ 10 ticks: 6.7%, max 268 ticks (29 bps)
- p50 = 1, p75 = 1, p90 = 7, p99 = 20 ticks — крайне асимметричное распределение
- Skewness +5.96, **kurtosis +101** — экстремальные spread-взрывы
- **AR(1) = +0.399** — между HYPE (0.334) и ZEC (0.593). Дискретные "взрывы" spread длятся мало

**Структура рынка:** DOGE сидит "приклеенный" к 1-tick spread, периодически
взрывается до 5–20 ticks при возмущениях, затем быстро возвращается. Это
**bimodal regime** — почти не существует "промежуточного" spread'а.

### Возвраты
- Stale (Δmid=0): **73.5%** — между AVAX/LINK (60–65%) и SOL/TIA (84%)
- Actual moves: 206,083, std = **0.854 bps**, kurtosis = **+79.8** — fat tails
- p50 move = 4 ticks, p95 = 16, p99 = 26, max = 401 ticks — крупные tail-движения
- σ(1s) = **0.655 bps/s** — **второй наименьший после TON** (0.565)
- σ(5min) = 13.7 bps
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH). Стандарт.

### Signature plot — лёгкий восходящий

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 0.655 | 0.655 |
| 5s | 1.706 | 0.763 |
| 15s | 3.037 | 0.784 |
| 30s | 4.283 | 0.782 |
| 1min | 5.899 | 0.762 |
| 5min | 13.826 | 0.798 |

σ/√sec растёт с 0.655 до 0.798 — небольшая momentum-составляющая (+22% за 5min).
Подобно SOL/ZEC, есть лёгкий тренд без mean reversion. Не Brownian, но близко.

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| **SOL** | 0.779 | ~5 | **0.16** ✅ |
| TON | 0.565 | 2.69 | 0.21 ✅ |
| TIA | 0.855 | 3.82 | 0.22 |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| ZEC | 1.341 | 1.01 | 1.33 ❌ |
| HYPE | 0.924 | 0.46 | 2.01 ❌ |
| **DOGE** | **0.655** | **0.28** | **2.34** ❌❌ |

**DOGE σ/spread = 2.34 — наихудший из семи.** Но это даже занижено: 80% времени
spread = 1 tick = 0.108 bps, тогда **σ/spread становится 6.0**. То есть в
доминирующем режиме рынок проходит **6 spread'ов за 1 секунду** — невозможная среда
для MM без edge-сигнала.

**Для стратегии:** котирование на 1-tick spread в DOGE — гарантированный
adverse selection. Реалистичный путь: котировать **глубже** L1, ловить
sweep-моменты когда spread временно расширяется. Это меняет стратегию с
**top-of-book MM** на **liquidity provision при дислокациях** — отдельный класс.

---

## §3 Order book structure

### L1 размер и симметрия
- L0: bid **77,827 DOGE ($7,180) / ask 60,711 DOGE ($5,597)** — bid/ask ratio 1.28×
- Median orders L1: **2 bid / 2 ask** (mean 2.05 / 1.93) — как у HYPE/ZEC
- Median order size L1: **11,063 / 13,668 DOGE** (~$1,020 / $1,260)
- p99 # orders: 8/7, max 61/48 — заметная queue-конкуренция, но не HYPE-уровня (max 127)
- При median 2 ордера × $1,140 ≈ **$2,280 typical L1 depth** — крупнее SOL ($1–2k), меньше HYPE

### Depth profile — **"вакуум" L1 как у SOL/HYPE/ZEC**

| Level | bid_sz | ask_sz | bid_n | ask_n | avg order bid ($) | avg order ask ($) |
|---|---|---|---|---|---|---|
| 0 (best) | 77,827 | 60,711 | 2.05 | 1.93 | 3,506 | 2,898 |
| 1 | **55,337** | **43,604** | 1.37 | 1.32 | 3,714 | 3,046 |
| 2 | 69,941 | 52,405 | 1.43 | 1.36 | 4,495 | 3,550 |
| 5 | 109,218 | 77,527 | 1.46 | 1.45 | 6,901 | 4,929 |
| 10 | 146,611 | 117,220 | 1.52 | 1.54 | 8,902 | 7,022 |
| 19 | 186,652 | 168,186 | 1.70 | 1.68 | 10,118 | 9,239 |

**L0 → L1 даёт провал −29%** (как у SOL). Затем монотонный рост до L15
(~$10–11k за ордер). Bid систематически глубже ask (1.28× на L0, до 1.5× на L19) —
**слабый long bias по структуре**.

### Microprice predictiveness — **умеренный, рабочий**

corr(imb_t, Δmid_{t+k}) на разных горизонтах k снапшотов:
- k=1: **+0.187** (≈ 537 ms)
- k=5: +0.113
- k=10: +0.085
- k=30: +0.054
- k=100: +0.032

Сравнение по семи активам: SOL +0.267, **DOGE +0.187**, AVAX/HYPE +0.157,
LINK +0.135, ZEC +0.130, TON +0.059, TIA +0.011.

**DOGE — второй после SOL по силе microprice сигнала.** Это значимое отличие
от HYPE/ZEC (где сигнал слабее) и подсказывает, что imbalance на DOGE
несёт реальную информацию — не просто noise.

**Для стратегии:** microprice — обязательный компонент fair value на DOGE.
Затухание к k=5 (0.113) → 2 снапшота (~1s). Edge "живёт" примерно секунду.

---

## §4 Trade analysis

### Масштаб активности
- **46,285 fills за 5 дней = 6.6/мин** — между TON (3) и ZEC (18)
- Total: 294,828,182 DOGE × $0.092 ≈ **$27M (одна сторона) → ~$10–11M/день**
- В **15× меньше** SOL ($200M), на уровне LINK ($12M)

### Структура участников сделок
- Buy 49.0% / Sell 51.0% по count, **48.3% / 51.7% по volume** — slight sell-bias
- Median trade size: **1,086 DOGE** (~$100). Mean: 6,370 DOGE (~$586). p99: 69,243 DOGE (~$6,370)
- p99 — крупные блоки $6k+, но они редки. Типичный таkер — $100–600

### Multi-leg sweeps
```
Taker legs: 46,285  →  unique events (по time_ms): 32,205  (69.6%)
```
**30.4% legs — части sweep'ов** — меньше чем у ZEC (54%) / HYPE (60%), на уровне
AVAX/LINK (~31%). DOGE рынок менее доминирован sweep-flow — большинство MO
точечно бьют L1.

### Inter-arrival — медленно-биполярно

| Метрика | Значение |
|---|---|
| Count | 46,284 |
| Mean Δt | 9,333 ms |
| p50 (median) | **1,746 ms (1.7 s)** |
| p90 | 30,029 ms (30 s) |
| p99 | 75,968 ms (76 s) |
| Max | 222 s |
| Δt < 50 ms | **30.5%** (burst-кластеры) |
| Δt > 1 s | 55.2% |
| Δt > 10 s | 26.1% |

Median Δt = 1.7s значит **половина соседних fill'ов разделены менее 2s**, что
указывает на нормальный non-burst режим (не как у ZEC где median 0). После
dedup по time_ms: λ̂_events = 0.07/sec = **4 уникальных MO/мин**.

**Для стратегии:** ожидайте 4 "истинных" MO/мин = ~1 fill/сторону в 30 секунд
при участии на L1. Это медленнее ZEC, но быстрее TON/TIA.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, p99 = 620 ms, max gap 405 s — стандарт
- **Trade-to-snapshot lag:** медиана 134 ms, mean 2,689 ms, p99 = 119s — типично

**Для стратегии:** обычные правила. Lag > 2s = не котировать.

---

## §6 Order book microstructure

### Churn — **умеренный**
- **Either bid/ask changed: 26.75%** снапшотов — между SOL (17%) и HYPE (32%)
- Bid changed 19.8%, ask changed 19.6% — симметрично
- **Median L1 lifetime: 506 ms** ≈ один snapshot — близко к SOL (527 ms)
- Mean lifetime 2,205 ms, p90 = 5,741 ms

**Уникально:** DOGE имеет **здоровую жизнь L1** (~500ms median) при tight spread.
Это лучше HYPE/ZEC (median 0ms). При HL-латентности 200ms у нас есть окно
~300ms для cancel/replace перед тем как L1 устаревает.

### L1 очередь
- Median 2 / 2 — как HYPE/ZEC. Mean 2.05 / 1.93
- p99 = 8 ордеров, max 61 — серьёзная конкуренция в редкие моменты
- Каждый ордер ~$1,100 — мелкие, но не HYPE-микро ($30)

**Для стратегии:** очередь жёсткая. Queue priority важна — поздно поставленный
ордер на 1-tick может вообще не получить fill за свою смену на L1.

---

## §7 Price dynamics

### σ at horizons
- σ(1s) = 0.655 bps, p99 = 2.11 bps
- σ(1min) = 6.08 bps
- σ(5min) = 13.7 bps (125 ticks)

### Range внутри окна
- median Range(1min) = **5.2 bps** — за минуту цена проходит ~50 ticks
- median Range(5min) тривиально не вычислен в этом дампе, но вытекает: ~13 bps = 119 ticks
- median Range(5s) = 0.53 bps — за 5 секунд диапазон ≈ 2× средний spread

**Соотношение range/spread:** за 1 минуту проходится Range/spread = 5.2/0.28 = **19 spread'ов**
— как у HYPE (15). Quote на минуту = гарантированная потеря.

**Stale quote horizon:** **<300 ms**. С σ(1s) = 0.655 bps и half-spread = 0.054 bps
(half-tick), прохождение half-spread занимает ~7ms в среднем (!). Quote должен
обновляться **каждые snapshot** (537ms) — практически на каждом тике LOB.

---

## §8 Fee economics

- **Effective maker rate: +0.100 bps** — **второй лучший после SOL** (−0.012)
- **Effective taker rate: +3.301 bps**
- **Round-trip cost: +3.401 bps**
- Maker fills с rebate: **60.9% count, 68.4% volume** — высокая top-tier пенетрация (вровень с ZEC 66.5%)
- Avg rebate per maker fill: −$0.015 USDC
- Avg taker fee: $0.192 USDC

### Базовая экономика для нашей base-tier стратегии

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier (we) | 0.28 bps | 3.0 bps | **−2.72 bps** (катастрофа!) |
| Top-tier rebate | 0.28 bps | −0.6 bps | +0.88 bps |

**Spread DOGE в 10× ниже base-tier break-even.** Даже на top-tier rebate edge
составляет всего +0.88 bps — самый узкий из всех "потенциально доходных"
активов. И это до учёта adverse selection.

### Сравнение всех семи:

| Актив | Mean spread | Edge top-tier | Edge base tier |
|---|---|---|---|
| SOL | 3–8 bps | +5.6 bps | +2 bps ✅ |
| TIA | 3.82 bps | +4.42 bps | +0.82 bps |
| TON | 2.69 bps | +3.29 bps | −0.31 bps |
| AVAX/LINK | 0.9–1.0 bps | +1.5 bps | −2 bps |
| ZEC | 1.01 bps | +1.61 bps | −1.99 bps |
| HYPE | 0.46 bps | +1.06 bps | −2.54 bps |
| **DOGE** | **0.28 bps** | **+0.88 bps** | **−2.72 bps** |

**DOGE имеет самый тонкий запас даже на top-tier.** Любая мисскалибровка
adverse selection ест весь edge — стратегия требует субтильной точности.

---

## §9 Funding rate

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:   +0.0496 bps/hr = +1.19 bps/day  (longs PAY shorts)
Std:          0.085 bps/hr  (умеренная вариативность)
Min rate:    -0.196 bps/hr  (мягкий негатив)
Max rate:    +0.125 bps/hr  (capped at floor)
p25/p50/p75: -0.012 / +0.087 / +0.125
Negative rate: 27.5% of hours
Mean premium: -4.16 bps (mark < oracle persistently)
```

### Профиль — **умеренный, сбалансированный**

DOGE funding занимает срединное положение:
- Не floor-pinned как TON/AVAX/LINK (там p25 = floor)
- Не extreme volatile как ZEC (std 0.338)
- Premium persistently negative (-4.16 bps) → market periodically pulls perp below oracle
- 72.5% часов rate ≥ 0 → лонги обычно платят шортам, но не всегда

### Сравнение funding по семи активам

| Актив | Mean rate bps/hr | Std | Negative% | Профиль |
|---|---|---|---|---|
| SOL | -0.013 | low | 51% | около нуля |
| TIA | -0.097 | low | 76.7% | стабильный негатив |
| ZEC | -0.102 | **0.338** | 39% | **волатильный** |
| HYPE | +0.060 | low | 19% | floor-positive |
| AVAX | +0.101 | low | low | floor-positive |
| LINK | +0.109 | low | low | floor-positive |
| TON | +0.117 | 0.034 | 2.5% | **floor-pinned positive** |
| **DOGE** | **+0.050** | **0.085** | **27.5%** | **умеренный mixed** |

### Финансовый эффект для MM

DOGE flow слегка sell-aggressor heavy (51.7% sell volume) → sell-takers бьют bid →
**MM-bid filled → MM в лонг**. При rate +0.05 bps/hr на лонг-инвентарь MM **платит**:
- 50,000 DOGE long × $0.092 × 0.05 bps/hr × 24h = **$0.55/день** (на $4,600 inventory)
- Пренебрежимо в среднем, как у SOL.

В худший час (-0.196 bps/hr) лонг **получает** $0.21/час — мелочь.

**Для стратегии:** funding на DOGE — около-нулевая строка. Не помогает, не мешает.

---

## §10 Market participants

### Концентрация
- **2,668 уникальных адресов** — между AVAX/LINK (~2,500) и ZEC (3,681)
- **Gini = 0.958** — высокая, стандарт для активного DEX-perpetual
- Top-5: **30.2%**, Top-20: **65.0%**, Top-100: **87.9%**

### Top-1: 0x348e5365... — pure directional taker

- 4,434 fills, **97.4% taker**, $5.31M volume, **net fee +$676** (нет rebate)
- Не MM. Крупный directional трейдер.

### Реальные pure-maker MM (rebate < 0)

Из топ-20:
- 0xecb63ca... — 100% maker, $2.85M, **rebate −$85** — серьёзный MM
- 0xd071d6d... — 100% maker, $2.71M, **rebate −$27**
- 0xadcbc1f... — 100% maker, $2.22M, **rebate −$67**
- 0xf9109ad... — 100% maker, $1.54M, **rebate −$46**

**Pure-maker top-tier: 4 видимых "стенда" $1.5–3M каждый.** Меньше чем на SOL/HYPE,
больше чем на TON. Конкуренция реальная но не доминирующая.

### Open vs Close flow

```
                    n   count_%  volume ($M)  volume_%
Close Long      20,553   22.2%       11.3        20.9%
Close Short     24,720   26.7%       12.9        23.9%
Long > Short     1,160    1.3%        1.6         3.0%
Open Long       20,461   22.1%       12.8        23.8%
Open Short     (visible incomplete; ~$14.4M / 26.7%)
Short > Long  (~$1.2M / 2.2%)
```

Estimated: **Open Long $12.8M vs Open Short ~$14.4M** — slight short bias по объёму
(53% short / 47% long opens). Это противоположно ZEC и HYPE (long-bias), ближе к
TON (strong short bias).

Что это значит для MM:
- Контрагенты openshort → продают агрессивно → бьют MM-bid → **MM в лонг**
- MM-long при rate > 0 (mean +0.05 bps/hr) → MM **платит** funding
- Эффект мал ($0.5/день на $5k) — не критично

### Open ≈ Close (50/50) — сбалансированный рынок

---

## Общий сравнительный профиль DOGE

| | SOL | HYPE | ZEC | **DOGE** | AVAX | LINK | TON | TIA |
|---|---|---|---|---|---|---|---|---|
| Объём/день | $200M | $160M | $31M | **$10M** | $15M | $12M | $4M | small |
| Mean spread | 3–8 bps | 0.46 | 1.01 | **0.28** ⚡ | 0.98 | 0.87 | 2.69 | 3.82 |
| σ(1s) bps | 0.779 | 0.924 | 1.341 | **0.655** | 0.743 | 0.678 | 0.565 | 0.855 |
| σ/spread | 0.16 ✅ | 2.01 | 1.33 | **2.34** ❌❌ | 0.76 | 0.78 | 0.21 | 0.22 |
| Microprice corr | +0.267 | +0.157 | +0.130 | **+0.187** | +0.157 | +0.135 | +0.059 | +0.011 |
| Stale % | 84% | 69% | 63% | **74%** | 60% | 65% | 91% | 84% |
| L1 lifetime (med) | 527 ms | 0 ms | 0 ms | **506 ms** ✓ | — | — | 2,672 ms | 1,041 ms |
| Churn % | 17% | 32% | 38% | **27%** | 40% | 35% | 8.8% | 16% |
| Trade rate /min | 50+ | 108 | 18 | **6.6** | 1 | 2 | 3 | 2 |
| Sweep legs % | ~13% | ~60% | 54% | **30%** | ~31% | ~31% | ~28% | ~17% |
| Funding mean | -0.013 | +0.060 | -0.102 | **+0.050** | +0.101 | +0.109 | +0.117 | -0.097 |
| Funding std | low | low | 0.338 | **0.085** | low | low | 0.034 | low |
| Flow bias | neutral | long | long | **short** | long | long | short | small short |
| Maker rebate % vol | 79.5% | 53.5% | 66.5% | **68.4%** | 49.4% | — | 32.4% | 43.6% |
| Eff. maker rate bps | -0.012 | +0.292 | +0.104 | **+0.100** ✓ | +0.190 | +0.250 | +0.334 | +0.151 |
| Unique users | 12,390 | 12,616 | 3,681 | **2,668** | 2,542 | 2,515 | 1,154 | 537 |
| Base tier viable? | ✅ | ❌ | ❌ | **❌❌** | ❌ | ❌ | ❌ | borderline |

⚡ = DOGE extreme: самый тесный spread (0.28 bps) и самое плохое σ/spread (2.34).
✓ = DOGE has healthier L1 lifetime than HYPE/ZEC, second-best maker rate.

---

## Ключевые параметры для AS-калибровки (если бы пришлось)

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.655 bps/s — второй низший после TON | §2 |
| σ/spread ratio | **2.34** — наихудший из семи | §2 |
| σ динамика | EWMA halflife 2–3 мин | §2 |
| Microprice edge | corr = **+0.187** — второй после SOL | §3 |
| L1 median orders | 2 bid / 2 ask | §6 |
| Median order size L1 | 11,063 DOGE = ~$1,020 | §3 |
| L1 lifetime | 506 ms median — здоровее HYPE/ZEC | §6 |
| Mean spread | 0.28 bps — **в 10× ниже base-tier break-even** | §8 |
| Tick precision | 0.108 bps/tick — самый "тонкий" из семи | §1 |
| Spread regime | 80% time = 1 tick, биполярно | §2 |
| Stale quote horizon | **<300 ms** — критически короткий | §7 |
| Snapshot cadence | 537 ms median — **больше stale horizon** ⚠️ | §5 |
| Funding (Apr 2026) | +0.050 bps/hr mean, std 0.085 — умеренный | §9 |
| MM inventory bias | LONG (из-за short-biased flow) | §10 |
| Funding эффект для MM | около-нулевой (~$0.5/день на $5k) | §9 |
| Expected trade rate | 6.6/min → ~3–4 unique MO/мин | §4 |
| Realistic order size | 1,000–10,000 DOGE ($90–900) | §3, §4 |

---

## Итог: DOGE — extreme spread + adverse selection cluster

### Где DOGE особенный среди семи

1. **Самый тесный spread (0.28 bps)** — на 40% уже HYPE (0.46 bps), на 70% уже ZEC.
2. **Наихудший σ/spread = 2.34** — несмотря на низкий абсолютный σ. Виноват extreme tight spread.
3. **Tick precision 0.108 bps** — рынок работает на минимальном возможном пенни-шаге для $0.09 цены.
4. **Bimodal spread regime** — 80% времени 1 tick, прыжки в 5+ ticks, почти нет промежуточного 2 ticks.

### Где DOGE лучше HYPE/ZEC

1. **Microprice corr +0.187** — второй после SOL. Imbalance несёт реальную информацию.
2. **L1 lifetime 506 ms** — здоровая жизнь best price. У HYPE/ZEC = 0 ms.
3. **Effective maker rate +0.100 bps** — второй лучший после SOL. 68.4% volume на rebate.
4. **Funding умеренный** — не floor-pinned (как TON), не volatile (как ZEC). Около-нулевой эффект для MM.
5. **Стабильная цена** — диапазон ~50 bps за 5 дней. В отличие от ZEC (12%) и HYPE.

### Где DOGE хуже HYPE/ZEC

1. **Объём $10M/день vs HYPE $160M, ZEC $31M.** В 3–16× меньше.
2. **Spread ещё уже** — top-tier edge всего +0.88 bps (vs HYPE +1.06, ZEC +1.61).
3. **30% sweep-legs (vs HYPE 60%, ZEC 54%)** — меньше toxic flow для capture, но и меньше
   "sweep-driven обновлений" L1.

### Рекомендация — обновлённый priority order

С учётом DOGE среди семи активов:

1. ✅ **SOL** — единственный жизнеспособный base-tier актив. Без вариантов.
2. ⚠️ **HYPE** — priority-2 после top-tier. $160M/день объёма компенсирует узкий edge.
3. ⚠️ **ZEC** — priority-3 после top-tier. Profile как HYPE, в 5× меньше объёма.
4. ⚠️ **DOGE** — priority-4. Tight spread cluster, **лучший micro-сигнал из low-spread группы**
   (+0.187 corr), здоровее L1 lifetime, но втрое меньше объёма ZEC.
5. ❌ AVAX / LINK / TON / TIA — все не жизнеспособны.

### DOGE не меняет наш план

Базовый запуск остаётся **на SOL**. DOGE можно рассматривать **после** валидации
SOL и получения top-tier maker discount — и **только если HYPE и ZEC уже работают**.

DOGE может быть интересен как **диверсификационный** актив в портфеле из 3+
активов: его correlation с SOL/BTC/ETH ниже чем у HYPE (специфический memecoin
драйверы), а microprice сигнал работающий. Но как **основной актив для старта** —
структурно непригоден из-за самого тесного spread на бирже.

### Уникальный риск DOGE: tick limitation

При цене $0.092 один tick = 0.108 bps. Спред физически не может быть уже одного tick.
Это значит:
- При нашем котировании на L1 = 1 tick spread мы конкурируем с MM, которые
  ставят на минимальном возможном расстоянии. Edge через "penny-jump" недоступен
  (1 tick = $0.000001 уже самый узкий).
- Чтобы расширить spread (например 2 ticks), нужно явно "уступать" L1.
- При L0/L1 разрыве 29% структура книги поощряет именно эту тактику (паркинг на L1
  при tight L0 spread).

Это **архитектурное** ограничение, отсутствующее на SOL ($83+ цена, tick $0.001 = 0.12 bps,
но spread обычно 3–8 bps = 30–80 ticks → есть много места для penny-jump).
