# TON-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.0001
**Цена:** $1.21–$1.26

TON — нативный токен The Open Network (Telegram). В нашей выборке из пяти активов
это **самый медленный** рынок по всем осям одновременно: самый низкий σ, самая
длинная жизнь L1, самый низкий churn, самый низкий notional ($4M/день). При
этом spread структурно **уже base-tier break-even** — серьёзная проблема для
старта.

---

## §1 General statistics

- LOB: **778,451** снапшотов, медианный интервал **537 ms** (идентично остальным четырём)
- Trades: **18,066 taker fills** за 5 дней → **0.04/sec (~3/min)** — на уровне TIA
- Total notional: ~$4M/день (грубая оценка по volume×price; в **40× меньше SOL**, в **3× меньше LINK**)
- Mean spread: **3.32 ticks = 2.69 bps** — между HYPE (0.46) и SOL (3–8 bps)
- Maker fills с rebate: **38.7%** (count), **32.4%** (volume) — самый низкий top-tier penetration из пяти

**Главное противоречие данных:** spread тесный (как у LINK/AVAX, 2.69 bps), но
активность низкая (как у TIA, 3 fills/min). У других активов корреляция активность↔spread
работает чётко: больше fills → уже spread. У TON оба показателя независимо плохие.

---

## §2 Asset overview

### Spread
- **Mean 2.69 bps (3.32 ticks)** — между AVAX/LINK (0.87–0.98) и TIA (3.82)
- p50=3, p75=4, p90=5, p99=7 ticks — компактное распределение
- **AR(1) spread = +0.901** — почти как у TIA (0.885), самый персистентный из пяти.
  Spread "залипает" — когда уходит от 3 ticks, держится там минутами.
- Skewness +0.79, kurtosis +6.31 — умеренный правый хвост (без HYPE-style взрывов)
- Max 50 ticks (40 bps) — было хотя бы раз за 5 дней
- = 1 tick: **10.0%** времени, = 2 ticks: **17.1%** времени, ≥ 5 ticks: **19.2%**
- **Нетривиально:** только 10% времени spread = 1 tick. У HYPE — 82%. У TON
  большую часть времени стакан *не максимально тесный*, в отличие от других
  низко-spread активов.

### Возвраты
- Stale (Δmid=0): **91.3%** — наибольший stale rate из пяти (SOL/TIA ~84%). Цена
  не двигается в 9 из 10 снапшотов.
- Actual moves: 67,738, std = **1.311 bps**, kurtosis = **+176** — экстремальные fat tails
- p50 move = 1 tick, p95 = 3, p99 = 5, max = 87 ticks
- σ(1s) = **0.565 bps/s** — **самый низкий из пяти** (SOL 0.779, TIA 0.855, AVAX 0.743, LINK 0.678, HYPE 0.924)
- σ(5min) = **12.0 bps** — тоже наименьший
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH — кластеризация). Как у всех.
- Signature plot: 0.565 (1s) → 0.694 (5min). Слегка возрастающий —
  лёгкая инерция/тренд, но в пределах sampling noise. Практически Brownian.

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| **SOL** | 0.779 | ~5 | **0.16** ✅ |
| **TON** | **0.565** | **2.69** | **0.21** ✅ |
| TIA | 0.855 | 3.82 | 0.22 |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| HYPE | 0.924 | 0.46 | 2.01 ❌ |

**TON: σ/spread = 0.21** — второй лучший после SOL. С точки зрения adverse selection
это **рабочий рынок**: рынок движется медленно относительно spread, котировка
успевает пожить до следующего движения. Это единственный положительный signal
из всех метрик TON.

**Для стратегии:** σ(1s) = 0.565 значит, что за 1s стандартное движение ≈ 0.7 tick,
а до half-spread (1.5 ticks) рынок дойдёт в среднем за ~5s. Это даёт окно
~5s "жизни" котировки без adverse selection — намного больше чем у HYPE (<1s).

---

## §3 Order book structure

### L1 размер и симметрия
- L0: bid **1,319 TON / ask 1,014 TON** — bid/ask ratio 1.30× (умеренная асимметрия)
- Median orders L1: **2 bid / 2 ask** (mean 2.13 / 2.41)
- Median order size L1: **511 TON bid / 446 TON ask** (~$634 / $553 при $1.24)
- p99: 6/7 ордеров, max 216/285 — пиковая конкуренция значительно ниже HYPE (max 127)
  но выше TIA (max ~10–20)

### Depth profile — **монотонный рост, без "вакуума"**

| Level | bid_sz | ask_sz | bid_n | ask_n | avg order bid | avg order ask |
|---|---|---|---|---|---|---|
| 0 (best) | 1,319 | 1,014 | 2.13 | 2.41 | 618 | 420 |
| 1 | 1,679 | 1,207 | 2.26 | 2.46 | 743 | 490 |
| 2 | 2,402 | 1,578 | 2.48 | 2.33 | 969 | 678 |
| 5 | 3,153 | 2,970 | 2.65 | 2.09 | 1,190 | 1,420 |
| 10 | 3,696 | 3,249 | 1.94 | 2.00 | 1,903 | 1,627 |
| 15 | 5,346 | 3,677 | 2.04 | 2.06 | 2,619 | 1,786 |
| 19 | 4,643 | 3,751 | 1.86 | 1.98 | 2,493 | 1,896 |

**Интерпретация:** В отличие от SOL/HYPE с провалом на L1–L3, у TON книга
растёт **монотонно** от L0 к L15 (как у TIA). Это значит: на L1 нет специальной
концентрации MM-ботов, конкурирующих за queue; пассивные ордера крупнее на дальних
уровнях.

**Bid систематически глубже ask** на всех 20 уровнях (отношение 1.3×). Microprice
поэтому слегка > mid в среднем (бычий бид по структуре).

### Microprice predictiveness — **очень слабый сигнал**

corr(imb_t, Δmid_{t+1}) на разных горизонтах k снапшотов:
- k=1: **+0.059** (≈ 537 ms)
- k=5: +0.055
- k=10: +0.056
- k=30: +0.052
- k=100: +0.044

**Сравнение:** SOL +0.267, AVAX/HYPE +0.157, LINK +0.135, TIA +0.011, **TON +0.059**.

TON между TIA (нулевой сигнал) и LINK (слабый рабочий). Imbalance не несёт
существенной предсказательной силы — fair value ≈ mid, microprice добавляет
очень мало.

**Для стратегии:** microprice как fair value на TON работает на грани значимости.
Использовать с малым весом или вообще не использовать; основной edge должен идти
от σ-skew и inventory skew, не от microprice.

---

## §4 Trade analysis

### Масштаб активности
- **18,066 fills за 5 дней = 3/мин** — в 36× медленнее HYPE, на уровне TIA
- Total volume: 2,615,552 TON ≈ **$3.24M (от taker side)**
- Open + Close notional (обе ноги): $42.8M / 5 дней → реальный flow **$4.3M/день**

### Структура участников сделок
- Buys 54.1% / Sells 45.9% по count, **56.1% / 43.9% по volume** — buy-bias
- Median trade size: **24 TON** (~$30). Mean: 145 TON (~$180). p99: 1,480 TON (~$1,840)
- Очень мелкие трейды — typical taker = розница с $30–180 ордером

### Multi-leg sweeps
```
Taker legs: 18,066  →  unique events (по time_ms): 13,089  (72.5%)
```
**27.5% legs — части sweep'ов** — меньше чем у HYPE (60%), TIA (16%), AVAX/LINK (31%).
Sweeps относительно редкие — большинство MO одноногие, бьющие точечно по L1.

### Inter-arrival — **очень медленный, биполярный режим**
- p10 = 0 ms (back-to-back sweep legs)
- p50 (median): **8,419 ms (8.4s)** — медленнее TIA (12s) лишь немного
- p90: 71,000 ms (71s) — минуты тишины обычны
- p99: 121,000 ms (~2 мин), max: 298,000 ms (5 мин)
- **Δt > 1s: 66.3%** пар trade-trade
- **Δt > 10s: 46.2%** — почти каждая вторая пара. Рынок "спит" половину времени.
- Δt < 50 ms: 27.59% — когда активен, торгуется в плотных burst'ах (sweep-legs)

**Для стратегии:** ожидайте 1 fill в каждую сторону **раз в 10–30 минут**.
Inventory накапливается медленно — это палка о двух концах: меньше fills → меньше
gross PnL, но и меньше adverse selection при stale quote (если не отменили вовремя
после движения).

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, mean 555 ms, p99 = 620 ms, max gap 405 секунд
- Δt > 1s: 0.018%, Δt > 10s: 0.010% — стандартное качество как у остальных
- **Trade-to-snapshot lag:** медиана 134 ms (норма), mean 2,165 ms, p99 = 99,948 ms
- Max lag 187s — в этих окнах нет данных, lob/трейды рассинхронизированы

**Для стратегии:** проверка свежести снапшота обязательна, как и для всех других
активов. Lag > 2s = не котировать.

---

## §6 Order book microstructure

### Churn — **самый низкий из пяти**
- **Either bid/ask changed: 8.83%** снапшотов — vs SOL 17%, AVAX 40%, HYPE 32%, LINK 35%, TIA 16%
- Bid changed 5.41%, ask changed 5.68% — почти симметрично
- **Median L1 lifetime: 2,672 ms** — vs SOL 527 ms, TIA 1,041 ms, HYPE 0 ms
  TON's L1 живёт **в 5× дольше** чем у SOL.
- Mean lifetime 9.2s, p90 = 26s, max = 406s

**Смысл:** TON's L1 — стабильный, "залипает". Если поставили ордер на L1 и он
не съеден трейдом, есть хорошие шансы что он простоит секундами без отмены.

### L1 очередь
- Median 2 ордера / сторону — как у HYPE, в отличие от TIA/AVAX/LINK (1)
- Размер ордера L1: median ~500 TON ($600) — мелкие
- max 285 ордеров — был хотя бы один эпизод массового котирования. Но p99 = 6, что
  означает "штатно" 2–6 ордеров, не реальная queue priority борьба как у HYPE.

**Для стратегии:** низкий churn + длинный L1 lifetime — комфортная среда для
квотинга. Не нужно перекотировать часто; cancel/replace редкие.

---

## §7 Price dynamics

### σ at multiple horizons (per √sec)

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 0.565 | 0.565 |
| 5s | 1.469 | 0.657 |
| 15s | 2.671 | 0.690 |
| 30s | 3.892 | 0.711 |
| 1min | 5.409 | 0.698 |
| 5min | 12.013 | 0.694 |

**Signature plot слегка возрастающий** — лёгкий тренд/инерция (mean reversion отсутствует),
но в пределах sampling noise. σ∝√T подтверждается на 5s–5min с точностью ±10%.

### Range внутри окна (5min)
- median = 3.6 bps, p90 = 9.9 bps, p99 = 23 bps
- За 5 минут типичный диапазон цены = 3.6 bps ≈ **1.3 spread'а**
- У SOL — 6 spread'ов, у HYPE — 15 spread'ов. **TON движется в spread'е намного дольше.**

**Stale quote horizon:** ~5–10s. При σ(1s) = 0.565 bps и spread 2.69 bps,
прохождение half-spread занимает в среднем 5s — то есть до 5–10s можно держать
котировку без значительного adverse selection.

**Для стратегии:** quote refresh раз в 2–5 секунд достаточно. Намного спокойнее
чем SOL (1–2s), не говоря о HYPE (<1s).

---

## §8 Fee economics

- **Effective maker rate: +0.334 bps** — хуже всех остальных (SOL −0.012, AVAX +0.190, LINK +0.250, TIA +0.151, HYPE +0.292)
- **Effective taker rate: +2.997 bps**
- **Round-trip cost: +3.331 bps**
- Maker fills с rebate: **38.7% count, 32.4% volume** — самый низкий top-tier penetration из пяти.
  Сравните: SOL 79.5% maker volume на rebate, HYPE 53.5%, AVAX 49.4%.
- Avg taker fee: **$0.054 USDC/fill** — намного меньше других (SOL/LINK ~$0.13–0.15) из-за крошечного notional ($180/fill)

### Базовая экономика для нашей base-tier стратегии

Round-trip при base tier (maker +1.5 + taker +4.5 = +6.0 bps на полный цикл, если делаем maker round-trip — то +3.0 bps):

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier | 2.69 bps | 3.0 bps | **−0.31 bps** (минус!) |
| Top-tier rebate | 2.69 bps | -0.6 bps | +3.29 bps |

**Spread TON структурно ниже base-tier break-even.** На каждый round-trip мы
теряем 0.3 bps **до** учёта adverse selection. Среди пяти активов:
- ✅ SOL: spread 3–8 bps → break-even проходит
- ❌ TON: spread 2.69 bps → ниже break-even
- ❌ AVAX/LINK: spread 0.9–1.0 bps → сильно ниже
- ❌ HYPE: spread 0.46 bps → катастрофически ниже
- ✅ TIA: spread 3.82 bps → break-even проходит, но микропризнаков нет

TON попадает в группу "structurally below break-even at base tier" — на старте $2-5k
капитала с base-tier fees стратегия проигрывает на one-way в среднем.

---

## §9 Funding rate — **самый высокий позитив из пяти**

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:   +0.1171 bps/hr = +2.81 bps/day  (longs PAY shorts)
Std:          0.034 bps/hr  (низкая вариативность)
Min:         -0.137 bps/hr  (один глубокий выброс)
Max:         +0.125 bps/hr  (capped at floor)
p25/p50/p75: 0.125 / 0.125 / 0.125
Negative rate: 2.5% of hours (только 6 часов из 240)
Mean premium:  -1.96 bps (mark < oracle persistently)
```

### Floor saturation — режим работы funding

**Quartiles p25=p50=p75=0.125 bps/hr** — значит **более 75% часов ставка
"приклеена" к теоретическому floor 0.125 bps/hr.** Это:
1. Premium ≤ 0.01%/8h порог практически всегда
2. Clamp ставит floor 0.01%/8h = 0.125 bps/hr
3. Лонги платят шортам по floor → шорты получают +0.125 bps/hr систематически

Premium стабильно отрицательный (mean −1.96 bps, max положительный лишь +0.68 bps).
Premium ≠ rate — premium показывает, что mark < oracle, но floor-mechanism
заставляет лонгов всё равно платить шортам.

### Финансовый эффект

При +0.117 bps/hr на короткой позиции:
- 1,000 TON short × $1.24 × 0.117 bps/hr × 24h = **+$0.35/день**
- 10,000 TON short × $1.24 × 0.117 bps/hr × 24h = **+$3.5/день**
- При $5k капитале и ±5k TON inventory: ~$1–2/день funding income (для шорта)

В **месяц** при стабильно ±5k TON шорт: ~$30–60/месяц. **Положительный**
постоянный денежный поток, **не зависящий от MM-стратегии**.

### Сравнение funding income/cost по пяти активам (на симметричном MM)

| Актив | Mean rate | Среднее MM-bias | Funding эффект для MM |
|---|---|---|---|
| SOL | −0.013 bps/hr | neutral | пренебрежимо |
| TIA | −0.097 bps/hr | neutral | ~$0.003/час на $300 — пренебрежимо |
| AVAX | +0.101 bps/hr | shorts (vs long-biased flow) | положительный |
| LINK | +0.109 bps/hr | shorts (vs long-biased flow) | положительный |
| HYPE | +0.060 bps/hr | shorts (vs long-biased flow) | +$10/день на 100 HYPE |
| **TON** | **+0.117 bps/hr** | **shorts** | **самый высокий позитив** |

**Для стратегии:** funding на TON — реальный pat. На MM который оказывается
короткой стороной (а это видимый short bias в данных — см. §10), funding
становится дополнительной строкой дохода, частично компенсирующей структурный
spread-deficit. Но эффект **слишком мал** ($1–2/день) чтобы вытащить базовую
экономику из минуса.

---

## §10 Market participants

### Концентрация
- **1,154 уникальных адресов** (между TIA 537 и SOL/HYPE ~12,400)
- **Gini = 0.939** — высокая, но мягче чем у SOL (0.977) и HYPE (0.964)
- Топ-5 = **44.9%**, Топ-20 = **72.2%**, Топ-100 = **91.7%** объёма
- Top-1 user (0x2a72...): 2,617 fills, 97% taker → крупный directional taker, не MM

### Структура флоу — **сильный short-bias в открытиях**

```
                    n   count_%  volume ($M)  volume_%
Close Long      19,090   17.2%        6.8        15.3%
Close Short     35,318   31.9%       14.7        33.0%
Open Long       18,637   16.8%        6.6        14.7%
Open Short      34,856   31.4%       14.6        32.6%

Open Long:  $6.6M (15%)   ←   реальный поток покупателей
Open Short: $14.6M (33%)  ←   в 2.2× больше
```

**Open Short по объёму в 2.2× больше Open Long** — это самый сильный directional
bias среди пяти активов. Пользователи в апреле 2026 систематически открывают
короткие позиции по TON.

Что это значит для MM:
- Когда контрагенты хотят шортить — они taker'ят ask → MM-bid filled → **MM остаётся в лонге** (получает то, что хотят сбросить)
- Систематический long bias inventory → MM платит funding (+0.117 bps/hr longs pay)
- **Funding эффект для MM на TON — отрицательный**, в отличие от моего раннего наивного предположения. ❗

### Уточнение по funding direction

Я выше написал что MM-шорт получает funding. Это верно по знаку (rate>0), но
неверно по типичной MM-позиции на TON:

- Toxic flow shorts agressivno → MM получает **buy-side** fills → MM-inventory лонг
- При rate +0.117 bps/hr × лонг inventory → MM **платит** funding
- Грубая оценка: $1.24 × 5,000 TON long × 0.117 bps/hr × 24h = **−$1.7/день funding cost**

Это **противоположно** ситуации с HYPE, где flow long-biased и MM-shorts получают
funding. На TON flow short-biased, MM-longs платят funding.

### Per-user maker/taker структура
- 0xecb63... — pure maker (100%), $0.34M volume, **net rebate −10.2 USDC** → real MM с top-tier
- 0x7717a7... — 93.5% maker, $0.25M, fee +13.7 USDC → не top-tier
- 0x57dd78... — pure maker, $0.21M, **rebate −4.2 USDC** → real MM
- 0xf9109a... — pure maker, $0.13M, **rebate −3.9 USDC** → real MM
- 0x010461... и 0x31ca83... — 30% maker hybrid, по $0.68M → крупный mixed trader

**Pure-maker top-tier участников с rebate: ≈ 3–4 видимых адреса**. Это намного
меньше "MM-стенда" SOL/HYPE. Рынок недо-обеспечен MM-конкуренцией.

---

## Общий сравнительный профиль TON

| | SOL | TON | TIA | LINK | AVAX | HYPE |
|---|---|---|---|---|---|---|
| Объём/день | $200M | **$4M** | small | $12M | $15M | $160M |
| Mean spread | 3–8 bps | 2.69 bps | 3.82 bps | 0.87 bps | 0.98 bps | 0.46 bps |
| σ(1s) bps | 0.779 | **0.565** | 0.855 | 0.678 | 0.743 | 0.924 |
| σ/spread | 0.16 ✅ | **0.21** ✅ | 0.22 | 0.78 ❌ | 0.76 ❌ | 2.01 ❌ |
| Microprice corr | +0.267 | **+0.059** | +0.011 | +0.135 | +0.157 | +0.157 |
| Stale % | 84% | **91.3%** | 84% | ~65% | ~60% | 69% |
| L1 lifetime | 527 ms | **2,672 ms** | 1,041 ms | — | — | 0 ms |
| Churn % | 17% | **8.8%** | 16% | 35% | 40% | 32% |
| Trade rate /min | 50+ | **3** | 2 | — | — | 108 |
| Funding mean | -0.013 | **+0.117** | -0.097 | +0.109 | +0.101 | +0.060 |
| Flow bias | neutral | **strong short** | small short | long | long | long |
| Maker rebate % vol | 79.5% | **32.4%** | 43.6% | — | 49.4% | 53.5% |
| Unique users | 12,390 | **1,154** | 537 | 2,515 | 2,542 | 12,616 |
| Base tier viable? | ✅ | **❌** | borderline ❌ | ❌ | ❌ | ❌ |

---

## Ключевые параметры для AS-калибровки (если бы пришлось)

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.565 bps/s — самый низкий из пяти | §2 |
| σ/spread ratio | 0.21 — рабочий, второй после SOL | §2 |
| σ динамика | EWMA halflife 2–3 мин | §2 |
| Microprice edge | corr = +0.059 — на грани значимости | §3 |
| L1 median orders | 2 per side | §6 |
| Median order size L1 | 511 TON bid / 446 TON ask | §3 |
| L1 lifetime | 2.7s — стабильная, реже перекотировать | §6 |
| Mean spread | 2.69 bps — **ниже base-tier break-even** | §8 |
| Break-even (base tier) | > 3 bps — **структурно недостижимо** | §8 |
| Stale quote horizon | 5–10s | §7 |
| Snapshot cadence | 537 ms median | §5 |
| Funding (Apr 2026) | +0.117 bps/hr (longs pay shorts, floor-pinned) | §9 |
| MM inventory bias | LONG (из-за short-biased flow) | §10 |
| Funding эффект для MM | **отрицательный**, ~$1–2/день на $5k | §9, §10 |
| Expected trade rate | 3/min → ~10–30 мин между fills | §4 |
| Realistic order size | 20–100 TON ($25–125) | §3, §4 |

---

## Итог: почему TON не подходит для старта

**Против (структурно):**

1. **Spread 2.69 bps < base-tier break-even 3.0 bps.** На round-trip мы теряем
   0.31 bps до учёта adverse selection. **Это нельзя обойти калибровкой.**
2. **Microprice +0.059** — почти нулевой сигнал. Edge через imbalance отсутствует.
3. **Trade rate 3/min** — fills редкие, inventory turnover медленный.
   При $5k капитале и target ±5k TON inventory: 1 fill в каждую сторону за 30 мин
   → 16 round-trips/час максимум.
4. **Funding для MM = отрицательный.** Flow short-biased → MM остаётся в лонге →
   платит +0.117 bps/hr на лонг.
5. **Top-tier penetration 32% volume** — рынок недо-обеспечен MM-конкуренцией,
   но это означает что MM-инфраструктура там ещё не сложилась (нет дешёвого
   spread-discovery).

**За (если бы рассматривать в будущем):**

1. **σ/spread = 0.21** — adverse selection структурно мягкая (как у SOL).
   Это значит: если бы spread был хотя бы 4 bps, TON был бы вторым по
   привлекательности после SOL.
2. **L1 lifetime 2.7s, churn 8.8%** — спокойный рынок, мало работы для cancel/replace.
3. **Самый низкий σ из пяти** — котировки относительно безопасны при размещении.
4. **Funding floor-pinned positive** — стабильный, предсказуемый. Минус для MM
   в данный период, но при flip к long-biased flow станет плюсом.
5. **Top-1 user is taker** — мало конкурентов на maker-side, легче проложить
   queue position.

**Рекомендация:** TON для нашего старта — **не подходит**. Spread структурно
ниже base-tier break-even, и единственный путь — top-tier rebate, который мы
получим только после набора объёма на других активах. SOL остаётся
единственным жизнеспособным базовым активом для запуска. TON можно вернуть в
рассмотрение **только после** получения top-tier maker discount — тогда
σ/spread=0.21 и низкий churn делают его потенциально вторым по привлекательности
после SOL.

**Главный вывод по сравнению с HYPE (priority-2 актив):** HYPE и TON оба
страдают от spread < break-even на base tier. Но HYPE компенсирует это
**объёмом** (108 fills/min × $160M/day notional), что превращает узкий edge в
большой абсолютный PnL. TON одновременно имеет тесный spread И низкую активность
(3 fills/min, $4M/day) — у него нет ни width-edge, ни volume-edge. **HYPE > TON**
как priority-2 кандидат при top-tier тарификации.
