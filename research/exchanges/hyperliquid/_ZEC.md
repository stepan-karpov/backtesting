# ZEC-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.01
**Цена:** $231.25–$258.37 (диапазон **12%** за 5 дней — сильный тренд)

ZEC — Zcash, privacy-coin старой школы (с 2016). В нашей выборке из шести
активов это **самый волатильный** рынок: σ(1s)=1.34 bps — выше HYPE (0.924).
При этом spread узкий (1 bps), как у LINK/AVAX. Комбинация даёт жёсткую среду
adverse selection, но с приличным объёмом ($31M/день) и хорошим top-tier
penetration. Профиль ближе всего к HYPE — высокая активность + наркотический
σ/spread, но меньшим масштабом.

---

## §1 General statistics

- LOB: **778,402** снапшотов, медианный интервал **537 ms** (как у всех)
- Trades: **132,051 taker fills** за 5 дней → **0.31/sec (18/min)** — третий по активности после HYPE (108/min) и SOL
- Total notional: **~$31M/день** (663,226 ZEC × $245 / 5 дней) — между AVAX/LINK ($12–15M) и HYPE ($160M)
- Mean spread: **2.45 ticks = 1.01 bps** — между LINK (0.87) и AVAX (0.98)
- Maker fills с rebate: **42.3% count, 66.5% volume** — высокий top-tier penetration

**Цена $231→$258 за 5 дней (+11.7%)** — strong directional regime. Это влияет
на funding, premium и flow интерпретацию: данные отражают трендовый период,
не нейтральный baseline.

---

## §2 Asset overview

### Spread
- **Mean 1.01 bps (2.45 ticks)** — узкий, между LINK/AVAX
- p50=1, p75=4, p90=5, p99=9 ticks — компактное распределение с длинным правым хвостом
- = 1 tick: **55.06%** времени — большую часть времени spread на минимуме
- = 2 ticks: 8.95%, ≥ 5 ticks: 16.4% — биполярное распределение: либо туго (1 tick), либо широко (4+)
- Skewness +2.91, kurtosis +35 — заметные взрывы (max 95 ticks = 39.2 bps)
- **AR(1) spread = +0.593** — самый низкий после HYPE (0.334). Spread динамичен,
  быстро возвращается к 1 tick после расширений.

### Возвраты
- Stale (Δmid=0): **63.0%** — **наименьший stale rate из шести!** SOL/TIA/TON = 84–91%, AVAX/LINK ~60–65%
- Actual moves: 287,927 — почти каждый снапшот цена двигается
- σ snapshot-to-snapshot = **1.555 bps**, kurtosis = **+31.9** (умеренные fat tails)
- p50 move = 2 ticks, p95 = 9, p99 = 15, max = 109 ticks
- σ(1s) = **1.341 bps/s** — **наивысший из шести** (HYPE 0.924, SOL 0.779)
- σ(5min) = **26.2 bps** — тоже наивысший
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH — кластеризация). Как у всех.

### Signature plot — лёгкий тренд

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 1.341 | 1.341 |
| 5s | 3.267 | 1.461 |
| 15s | 5.805 | 1.499 |
| 30s | 8.184 | 1.494 |
| 1min | 11.561 | 1.492 |
| 5min | 26.231 | 1.514 |

Слегка возрастающий — ~13% разрыв между 1s и 5min. Лёгкое **momentum-смещение**,
консистентное с трендовым движением цены на 12% за 5 дней. **Без mean reversion.**

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| **SOL** | 0.779 | ~5 | **0.16** ✅ |
| TON | 0.565 | 2.69 | 0.21 ✅ |
| TIA | 0.855 | 3.82 | 0.22 |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| **ZEC** | **1.341** | **1.01** | **1.33** ❌ |
| HYPE | 0.924 | 0.46 | 2.01 ❌ |

**ZEC: σ/spread = 1.33** — второй худший после HYPE. Рынок проходит 1.3 spread'а
за 1 секунду. Quote, поставленный на best price, в среднем сгорает быстрее чем за секунду.

**Для стратегии:** σ(1s) = 1.34 bps + spread 1.01 bps — без edge-сигнала котирование
на L1 даёт гарантированный adverse selection. Половина-spread (0.5 bps)
проходится в среднем за **(0.5/1.34)² ≈ 140 ms**. Это HYPE-class adverse selection
при HYPE-class фоновой ликвидности.

---

## §3 Order book structure

### L1 размер и симметрия
- L0: bid **19.2 ZEC ($4,700) / ask 16.9 ZEC ($4,140)** — bid/ask ratio 1.14× (симметрично)
- Median orders L1: **1 bid / 2 ask** (mean 1.88 / 2.03) — больше похоже на AVAX/LINK чем на HYPE
- Median order size L1: **2.54 / 2.62 ZEC** (~$622 / $641 при $245)
- p99: 8/8 ордеров, max 28/25 — нет HYPE-style "поля боя" из 100+ ордеров
- При среднем 2 ордера × $640 ≈ $1280 typical L1 depth — на уровне SOL ($1k–2k)

### Depth profile — "вакуум" L1 (как у SOL/HYPE)

| Level | bid_sz | ask_sz | bid_n | ask_n | avg order bid ($) | avg order ask ($) |
|---|---|---|---|---|---|---|
| 0 (best) | 19.2 | 16.9 | 1.88 | 2.03 | 2,494 | 2,036 |
| 1 | **16.2** | **17.2** | 1.66 | 1.76 | 2,391 | 2,403 |
| 2 | 20.5 | 21.3 | 1.84 | 1.89 | 2,729 | 2,766 |
| 5 | 32.2 | 33.2 | 2.07 | 2.13 | 3,805 | 3,822 |
| 10 | 48.4 | 48.9 | 2.22 | 2.42 | 5,346 | 4,942 |
| 15 | 52.4 | 53.0 | 2.34 | 2.44 | 5,486 | 5,314 |
| 19 | 50.4 | 52.2 | 2.31 | 2.42 | 5,351 | 5,278 |

**Интерпретация:** L0 → L1 даёт небольшой провал (−15% на bid), затем монотонный
рост до L15. Паттерн **слабый "вакуум"** — менее выраженный чем у SOL (−30%) и
HYPE (−44%), но всё равно есть. Bids и asks почти зеркально симметричны на всех 20 уровнях.

### Microprice predictiveness — **умеренный сигнал**

corr(imb_t, Δmid_{t+k}) на разных горизонтах k снапшотов:
- k=1: **+0.130** (≈ 537 ms)
- k=5: +0.082
- k=10: +0.064
- k=30: +0.040
- k=100: +0.024

Сравнение по шести активам: SOL +0.267, AVAX/HYPE +0.157, **LINK +0.135 ≈ ZEC +0.130**,
TON +0.059, TIA +0.011.

ZEC сидит рядом с LINK — умеренный рабочий сигнал. Лучше чем TON/TIA, но в 2× слабее SOL.
Быстрое затухание к k=5 (0.082) говорит что imbalance "живёт" 2–3 снапшота (≈1.5s).

**Для стратегии:** microprice как fair value на ZEC даёт edge, но небольшой.
Полезен, но не доминирующий компонент стратегии. Основной риск — короткое
"время жизни" сигнала (1.5s) при σ/spread=1.33.

---

## §4 Trade analysis

### Масштаб активности
- **132,051 fills за 5 дней = 18/мин** — третий по активности (HYPE 108, SOL ~60+)
- Total ZEC volume: 663,226 × $245 ≈ **$162M / 5 дней = $32M/день**
- В **8×** активнее AVAX/LINK ($12–15M), в **8× меньше** SOL ($200M)

### Структура участников сделок
- Buy 51.8% / Sell 48.2% по count, **48.8% / 51.2% по volume** — слегка sell-bias по объёму
- Median trade size: **1.33 ZEC** (~$326). Mean: 5.02 ZEC (~$1,229). p99: 67.7 ZEC (~$16,587)
- **Большие notional трейды** — крупнейший median trade size среди шести активов (по $). У HYPE median $221, SOL ~$10–50.

### Multi-leg sweeps — **рекорд из шести**
```
Taker legs: 132,051  →  unique events (по time_ms): 61,066  (46.2%)
```
**53.8% legs — части sweep'ов** — больше чем у HYPE (60% наоборот, у HYPE
40.2% unique → 59.8% sweep). Wait — на самом деле HYPE имеет 59.8% sweep legs,
а ZEC 53.8%. ZEC второй после HYPE по sweep-доминированию.

Sweep-heavy рынок означает: один MO часто метёт несколько уровней, типичный
"taker tick" — это очередь из 2–3 заполненных уровней подряд за < 10 ms.

### Inter-arrival — биполярный режим

| Метрика | Значение |
|---|---|
| Count | 132,050 |
| Mean Δt | 3,271 ms |
| **p50 (median)** | **0 ms** (sweep-legs back-to-back) |
| p90 | 10,365 ms (10.4 s) |
| p99 | 38,542 ms (38.5 s) |
| Max | 255 s |
| Δt < 50 ms | **53.85%** — burst-доминирование |
| Δt > 1 s | 33.4% |
| Δt > 10 s | 10.4% |

Median = 0 ms — половина соседних fill'ов разделены менее чем миллисекундой
(внутри одного sweep). После dedup по `time_ms`: 61,066 уникальных событий →
λ̂_events = 0.14/sec → **8.4 уникальных MO/мин**.

**Для стратегии:** ожидайте 8–9 "истинных" MO/мин. Каждый второй MO — sweep,
проходящий через 2+ уровня. Обнаружение **первого legs of sweep** = немедленная
отмена котировок дальше по сторону.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, mean 555 ms, p99 = 620 ms, max gap 405 s
- Δt > 1s: 0.018%, Δt > 10s: 0.010% — стандарт.
- **Trade-to-snapshot lag:** медиана 134 ms, mean 2,432 ms, p99 = 110,637 ms — типично

**Для стратегии:** проверка свежести снапшота обязательна. Lag > 2s = не котировать.

---

## §6 Order book microstructure

### Churn — **очень высокий**
- **Either bid/ask changed: 37.99%** снапшотов — третий после AVAX (40%) и LINK (35%)
- Bid changed 29.5%, ask changed 26.4% — симметрично
- **Median L1 lifetime: 0 ms** — L1 меняется **быстрее snapshot cadence**, как у HYPE.
  Это значит реальный churn существенно выше видимого.
- Mean lifetime 1,393 ms, p90 = 3,764 ms

### L1 очередь — компактная
- Median 1 bid / 2 ask — между HYPE (median 2) и AVAX/LINK (median 1)
- Mean 1.88 bid / 2.03 ask
- p99 = 8 — серьёзная конкуренция в редких моментах, но не HYPE-уровня (max 127)
- max 28 ордеров — было хотя бы раз за период

**Для стратегии:** L1 живёт <500 ms — нужна агрессивная переотметка котировок.
При HL-латентности 200 ms на cancel/place у нас есть окно ~1–2s до того, как
котировка устаревает. Cancel-before-taker priority HL здесь принципиально важна.

---

## §7 Price dynamics

### σ at multiple horizons
- σ(1s) = **1.341 bps**, p99 = 4.16 bps (10 ticks)
- σ(5min) = **26.2 bps** (64 ticks)
- σ(1min) = 11.6 bps (28 ticks)

### Range внутри окна
- median Range(5min) = **11.4 bps** — за 5 минут типичный диапазон цены = **11 spread'ов**
- p99 Range(5min) = **48 bps** — почти 50 spread'ов в редких эпизодах
- Сравните: SOL Range(5min) ~ 6 spread, HYPE ~ 15, TON ~ 1.3

**ZEC проходит 11 spread'ов за 5 минут.** Это HYPE-уровень адверсной селекции
в долгом горизонте. Quote, не обновлённый 5 минут, гарантированно проигрывает.

**Stale quote horizon:** **<500 ms**. При σ(1s) = 1.34 bps и half-spread = 0.5 bps,
прохождение половины спреда занимает 140–200 ms. Quote должен обновляться
каждые 200–500 ms — на пределе HL latency.

---

## §8 Fee economics

- **Effective maker rate: +0.104 bps** — между SOL (−0.012) и TIA (+0.151). Низкий cost.
- **Effective taker rate: +3.646 bps** — выше среднего (большие notional трейды → больше adj. fee)
- **Round-trip cost: +3.750 bps**
- Maker fills с rebate: **42.3% count, 66.5% volume** — высокий top-tier penetration
- Avg rebate per maker fill: −$0.048 USDC (большой notional)
- Avg taker fee: **$0.45 USDC/fill** — самый большой из шести (большой notional ~$1k)

### Базовая экономика для нашей base-tier стратегии

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier (we) | 1.01 bps | 3.0 bps | **−1.99 bps** (минус!) |
| Top-tier rebate | 1.01 bps | −0.6 bps | +1.61 bps |

**Spread ZEC структурно ниже base-tier break-even.** На каждый round-trip
теряем 2.0 bps **до** учёта adverse selection. Среди шести активов:
- ✅ SOL: spread 3–8 bps → break-even проходит
- ❌ ZEC: spread 1.01 bps → ниже break-even на 2.0 bps
- ❌ TON: spread 2.69 bps → ниже на 0.3 bps
- ❌ AVAX/LINK: spread 0.9–1.0 bps → ниже на 2.0 bps
- ❌ HYPE: spread 0.46 bps → ниже на 2.5 bps
- ✅ TIA: spread 3.82 bps → break-even проходит, но микропризнаков нет

ZEC попадает в "HYPE-cluster": тесный spread + высокая активность. На top-tier
становится потенциально доходным; на base tier — структурно убыточным.

---

## §9 Funding rate — **самый волатильный из шести**

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:    -0.1021 bps/hr = -2.45 bps/day  (longs EARN, shorts pay)
Std:           0.338 bps/hr  (НА ПОРЯДОК выше остальных)
Min rate:    -1.390 bps/hr  (!) — экстремальный негатив
Max rate:    +0.125 bps/hr  (capped at floor)
p25/p50/p75: -0.259 / +0.125 / +0.125
Negative rate: 39.2% of hours (vs SOL 51%, TIA 76.7%)
Mean premium: -4.99 bps (mark < oracle persistently — strong discount)
```

### Биполярная динамика

ZEC funding имеет **самую высокую вариативность** из шести (std=0.338 vs 0.034 у TON):
- **61% времени:** rate приклеена к floor +0.125 bps/hr (longs pay shorts)
- **39% времени:** rate глубоко отрицательная — до **−1.39 bps/hr** (!)

Это **в 10× более экстремальный негатив** чем у любого другого актива
(TON min −0.137, HYPE min −0.451, TIA min ≈ −0.5). ZEC funding ходит между
"спокойно" и "паника шортов крайне дорогая".

### Финансовый эффект для MM

Flow long-biased ($86M Open Long vs $70.7M Open Short — см. §10) →
MM системно оказывается в шорт-позиции → при mean rate −0.102 bps/hr (negative)
MM-шорт **платит** funding:

- 100 ZEC short × $245 × 0.102 bps/hr × 24h = **$0.60/день** при mean rate
- В худший час: 100 ZEC short × $245 × 1.39 bps/hr × 1h = **−$0.34/час** = up to $8/час на короткой позиции
- На $5k капитала и ±20 ZEC inventory: ~$0.10/день — пренебрежимо в среднем,
  но катастрофические выбросы в плохие часы

**Главное:** funding-волатильность ZEC означает нужно мониторить ставку **отдельно**
и адаптировать inventory limit. При rate < −0.5 bps/hr (быстрая дешёвка шорта)
лучше держать flat или long.

---

## §10 Market participants

### Концентрация
- **3,681 уникальных адресов** — между AVAX/LINK (~2,500) и SOL/HYPE (12k+)
- **Gini = 0.960** — высокая, типичная для активного DEX-актива
- Top-5: **30.3%**, Top-20: 55.3%, Top-100: 82.4%

### Top-1 user: 0xb4321b...
- **9,959 fills**, 39.4% maker, $48.04M volume — самый крупный, но не pure MM
- Net fee $1,192 — платил taker fee, не получил rebate (значит не top-tier)
- Это крупный гибридный directional трейдер, не настоящий market maker

### Реальные top-tier MM (pure maker + rebate)

Идентификация по `maker_share=100%` AND `net fee < 0`:
- 0xd071d6... — 100% maker, $17.4M, **rebate −$174** — серьёзный MM
- 0xf9109a... — 98.8% maker, $10.4M, **rebate −$295** — top MM
- 0x0622a2... — 90.8% maker, $8.3M, **rebate −$175**
- 0x7717a7... — 98.7% maker, $7.9M, +$284 — high maker но не top-tier rebate
- 0x57dd78... — 86.1% maker, $7.1M, +$35

**Pure-maker top-tier "стенд": 3–4 серьёзных конкурента** с $8–17M объёма каждый.
Это меньше чем на SOL/HYPE, но больше чем на AVAX/LINK/TON.

### Open vs Close flow — **long-biased**

```
                    n       count_%  volume ($M)  volume_%
Close Long      62,129       23.5%       85.9        26.6%
Close Short     60,871       23.0%       69.6        21.6%
Open Long       67,280       25.5%       86.0        26.6%
Open Short      66,226       25.1%       70.7        21.9%

Open Long:  $86.0M (54.9%)   ←   доминирующий поток
Open Short: $70.7M (45.1%)
```

**Open Long в 1.22× больше Open Short по объёму.** Контрагенты в апреле 2026
активно лонговали ZEC — консистентно с +11.7% движением цены.

Что это значит для MM:
- Контрагенты taker'ят ask → MM-asks filled → MM в шорт-позиции
- При rate < 0 → MM **платит** funding (mean -0.102 bps/hr на шорт)
- **Funding эффект для MM на ZEC — отрицательный**, как и на TON

### Open ≈ Close (50.2% / 49.8%)

Рынок не накапливает существенный directional bias на горизонте 5 дней —
inflows ≈ outflows, несмотря на price move. Это нормально для активного perp.

---

## Общий сравнительный профиль ZEC

| | SOL | HYPE | **ZEC** | AVAX | LINK | TON | TIA |
|---|---|---|---|---|---|---|---|
| Объём/день | $200M | $160M | **$31M** | $15M | $12M | $4M | small |
| Mean spread | 3–8 bps | 0.46 bps | **1.01 bps** | 0.98 bps | 0.87 bps | 2.69 bps | 3.82 bps |
| σ(1s) bps | 0.779 | 0.924 | **1.341** ⚡ | 0.743 | 0.678 | 0.565 | 0.855 |
| σ/spread | 0.16 ✅ | 2.01 ❌ | **1.33** ❌ | 0.76 | 0.78 | 0.21 | 0.22 |
| Microprice corr | +0.267 | +0.157 | **+0.130** | +0.157 | +0.135 | +0.059 | +0.011 |
| Stale % | 84% | 69% | **63%** ⚡ | 60% | 65% | 91% | 84% |
| L1 lifetime (med) | 527 ms | 0 ms | **0 ms** | — | — | 2,672 ms | 1,041 ms |
| Churn % | 17% | 32% | **38%** | 40% | 35% | 8.8% | 16% |
| Trade rate /min | 50+ | 108 | **18** | 1 | 2 | 3 | 2 |
| Sweep legs % | ~13% | ~60% | **54%** | ~31% | ~31% | ~28% | ~17% |
| Funding mean | -0.013 | +0.060 | **-0.102** | +0.101 | +0.109 | +0.117 | -0.097 |
| Funding std | low | low | **0.338** ⚡ | low | low | 0.034 | low |
| Flow bias | neutral | long | **long** | long | long | short | small short |
| Maker rebate % vol | 79.5% | 53.5% | **66.5%** | 49.4% | — | 32.4% | 43.6% |
| Unique users | 12,390 | 12,616 | **3,681** | 2,542 | 2,515 | 1,154 | 537 |
| Base tier viable? | ✅ | ❌ | **❌** | ❌ | ❌ | ❌ | borderline |

⚡ = ZEC extreme: самый высокий σ, самый низкий stale, самая волатильная funding.

---

## Ключевые параметры для AS-калибровки (если бы пришлось)

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | **1.341 bps/s** — наивысший из шести | §2 |
| σ/spread ratio | 1.33 — второй худший после HYPE | §2 |
| σ динамика | EWMA halflife 2–3 мин | §2 |
| Microprice edge | corr = +0.130 — умеренный, как LINK | §3 |
| L1 median orders | 1 bid / 2 ask | §6 |
| Median order size L1 | 2.54 ZEC = ~$622 | §3 |
| L1 lifetime | **<500 ms** — нужен быстрый refresh | §6 |
| Mean spread | 1.01 bps — **ниже base-tier break-even** | §8 |
| Break-even (base tier) | > 3 bps — **структурно недостижимо** | §8 |
| Stale quote horizon | **200–500 ms** — критически короткий | §7 |
| Snapshot cadence | 537 ms median — **больше stale horizon** ⚠️ | §5 |
| Funding (Apr 2026) | −0.102 bps/hr mean, std 0.338 — **волатильное** | §9 |
| Funding worst case | −1.39 bps/hr (10× любого другого актива) | §9 |
| MM inventory bias | SHORT (из-за long-biased flow) | §10 |
| Funding эффект для MM | отрицательный mean, экстремальные spikes | §9, §10 |
| Expected trade rate | 18/min → ~3 fills/сторону в минуту | §4 |
| Realistic order size | 0.5–2 ZEC ($125–500) | §3, §4 |

---

## Итог: ZEC — HYPE-cluster с меньшим объёмом

### Структурное сходство с HYPE

ZEC и HYPE — два актива с одинаковым **профилем риска**:
- Тесный spread (0.46 bps HYPE, 1.01 bps ZEC) ниже base-tier break-even
- Высокий σ (0.924 / 1.341 bps/s) → high adverse selection
- σ/spread > 1 (2.01 / 1.33) → quote сгорает за < 1s
- L1 lifetime ≈ 0 ms — fast churn, требует быстрого cancel/replace
- High sweep proportion (60% / 54%) — burst-доминируемая активность
- Long-biased flow → MM-shorts → funding cost риск

### Где ZEC хуже HYPE

1. **Объём $31M/день vs $160M/день** — в 5× меньше. Меньше fills →
   меньше edge даже при одинаковом per-fill PnL.
2. **σ ещё выше** — 1.341 vs 0.924 bps. Adverse selection ещё жёстче.
3. **Funding гораздо более волатильный** — std 0.338 vs 0.034 у TON.
   Min −1.39 bps/hr (vs −0.45 у HYPE) — экстремальные шипы.
4. **Меньше уникальных юзеров** — 3.7k vs 12.6k. Меньше "наивных" розничных контрагентов.

### Где ZEC лучше HYPE

1. **σ/spread 1.33 < 2.01** — adverse selection относительно мягче.
2. **Effective maker rate +0.104 vs +0.292** — лучшая fee economics для maker'ов.
3. **Microprice +0.130 ≈ +0.157** — сопоставимый сигнал.
4. **Большие notional трейды** ($1k+ median) — каждый fill значимее.

### Рекомендация для нашего старта

**Priority order среди шести активов:**

1. ✅ **SOL** — единственный жизнеспособный base-tier актив (spread 3–8 bps > 3 bps break-even, σ/spread 0.16, microprice +0.267)
2. ⚠️ **HYPE** — priority-2 после top-tier. $160M/день объёма даёт большой абсолютный PnL даже при узком edge.
3. ⚠️ **ZEC** — priority-3 после top-tier. По профилю как HYPE, но в 5× меньше объёма и в 10× более рискованный funding. Не имеет ни уникального преимущества (как SOL для base-tier), ни volume-edge (как HYPE для top-tier).
4. ❌ AVAX/LINK/TON/TIA — не жизнеспособны.

**ZEC не меняет наш план.** Базовый старт остаётся на SOL. ZEC можно
рассматривать **после** валидации стратегии на SOL и получения top-tier maker discount,
но **только если HYPE уже работает** — иначе ZEC даёт ту же экспозицию к рискам с
меньшим upside.

### Уникальный риск ZEC: трендовый период данных

**12% движение цены за 5 дней апреля 2026 — нерепрезентативная выборка.** AS-модель,
калиброванная на трендовом периоде, может неправильно оценивать:
- σ (искусственно завышена за счёт directional drift)
- Microprice corr (часть predictiveness идёт от trend follow-through, а не от
  истинного imbalance)
- Funding regime (39% часов в негативной зоне — может быть нетипично)

Для корректной калибровки ZEC нужны **30+ дней разных режимов** (бык/медведь/ranging).
В этом ZEC более требователен к данным чем SOL/HYPE, где апрель 2026 выглядит более
нейтрально.
