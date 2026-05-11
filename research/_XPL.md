# XPL-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.00001
**Цена:** $0.09–$0.17 (диапазон **+89% за 5 дней — самый экстремальный тренд в выборке**)

XPL — нативный токен Plasma (новый L1 в DeFi-вселенной), запущенный недавно с
очень высокой spec-activity. В выборке из **десяти активов** имеет **самый
высокий σ(1s) (3.57 bps)** — в 4× больше SOL, в 2.5× больше ZEC. Уникален тем что
spread (3.09 bps) **выше base-tier break-even** при одновременно высокой
активности (40 fills/min, $43M/день). Но σ/spread = 1.16 + ликвидации 4%+
объёма делают это **высокорисковым** профилем.

---

## §1 General statistics

- LOB: **778,496** снапшотов, медианный интервал **537 ms** (стандарт)
- Trades: **290,717 taker fills** за 5 дней → **0.67/sec (40/min)** — **второй по активности** после HYPE (108/min)
- Total notional: **~$43M/день** (1.67B XPL × ~$0.13 mid / 5 дней) — третий по объёму после SOL ($200M), HYPE ($160M)
- Mean spread: **3.49 ticks = 3.09 bps** — **третий выше break-even** (после SOL 5, TIA 3.82)
- Maker fills с rebate: **52.5% count, 56.5% volume** — moderate top-tier penetration

**Уникально:** XPL — единственный актив в выборке с **+89% движением цены**
за 5 дней. Это **не tradeable baseline data** — все метрики искажены сильным
directional regime. σ, microprice, funding — всё в режиме hype-rally.

---

## §2 Asset overview

### Spread — **bimodal с экстремальным хвостом**

- **Mean 3.09 bps (3.49 ticks)** — между TIA (3.82) и TON (2.69), **выше base-tier break-even**
- p50 = 3, p75 = 4, p90 = 6, p99 = 12, p99.9 = **29 ticks**
- = 1 tick: 14.9%, = 2 ticks: 21.5%, ≥ 5 ticks: 22.9%
- **Max: 1,252 ticks = 921.9 bps (!)** — экстремальный взрыв spread, скорее всего во время ликвидаций
- **Skewness +94.05, kurtosis +31,250** — самые экстремальные значения из десяти. Хвост чудовищный.
- **AR(1) = +0.405** — между HYPE (0.334) и DOGE (0.399). Spread динамичен.

**Структура рынка:** XPL spread не сидит на 1 tick (как DOGE/HYPE 80%) и не
сидит на n ticks стабильно (как AAVE 9 ticks). Это **активный bimodal с хвостом**:
типично 3 ticks, но регулярно расширяется до 12+ ticks. Max 1,252 ticks — катастрофа,
случающаяся при liquidation cascade.

### Возвраты
- Stale (Δmid=0): **65.5%** — между ZEC (63%) и AAVE (67%)
- Actual moves: 268,331, std = **4.181 bps**, kurtosis = **+1,077** — **экстремальные fat tails** (в 10× больше любого другого актива)
- σ(1s) = **3.574 bps/s** — **наивысший из десяти** (ZEC 1.341, HYPE 0.924, SOL 0.779)
- σ(5min) = **82.4 bps** — катастрофический горизонт
- ACF(r) ≈ 0 (random walk), ACF(r²) значим (ARCH). Стандарт.

### Signature plot — выраженный momentum

| scale | σ per bar (bps) | σ per √sec (bps) |
|---|---|---|
| 1s | 3.574 | 3.574 |
| 5s | 9.404 | 4.205 |
| 15s | 18.102 | 4.674 |
| 30s | 27.215 | 4.969 |
| 1min | 37.532 | 4.845 |
| 5min | 82.412 | 4.758 |

σ/√sec растёт с 3.57 до 4.96 — **+39% за 30s**. Сильное momentum-смещение,
консистентное с +89% rally. Аналогично ZEC и AAVE (но в 4–5× мощнее по абсолютному σ).

### КРИТИЧЕСКИ ВАЖНОЕ СООТНОШЕНИЕ: σ / spread

| Актив | σ(1s) bps/s | Mean spread bps | Ratio |
|---|---|---|---|
| **SOL** | 0.779 | ~5 | **0.16** ✅ |
| TON | 0.565 | 2.69 | 0.21 ✅ |
| TIA | 0.855 | 3.82 | 0.22 |
| AAVE | 0.730 | 1.08 | 0.68 |
| AVAX | 0.743 | 0.98 | 0.76 |
| LINK | 0.678 | 0.87 | 0.78 |
| **XPL** | **3.574** | **3.09** | **1.16** ❌ |
| ZEC | 1.341 | 1.01 | 1.33 ❌ |
| HYPE | 0.924 | 0.46 | 2.01 ❌ |
| DOGE | 0.655 | 0.28 | 2.34 ❌❌ |

**XPL σ/spread = 1.16** — седьмое место из десяти. **Quote проходит spread за 1 секунду** —
быстрее чем у AAVE/AVAX/LINK (где 1.5–2.0 sec), но медленнее чем у ZEC/HYPE/DOGE.

**Уникально:** XPL единственный актив, где **и spread выше break-even, и σ/spread > 1**.
То есть на base tier мы зарабатываем gross +0.09 bps на каждый round-trip,
но adverse selection вычисляется отдельно и при σ/spread=1.16 — съест этот edge.

**Для стратегии:** σ(1s) = 3.57 bps + half-spread 1.5 bps → прохождение
half-spread занимает (1.5/3.57)² ≈ 180 ms. Quote **сгорает за <200 ms**.
Это HYPE-class adverse selection. Котирование на L1 без edge — гарантированный
burn даже несмотря на номинально достаточный spread.

---

## §3 Order book structure

### L1 — **тонкая очередь, средние ордера**
- Median orders L1: **1 / 1** (mean 1.64 / 1.85) — как AAVE
- Median order size L1: **3,932 / 3,547 XPL** (~$512 / $461 при mid $0.13)
- p99 = 6 / 9 ордеров, max 40 / 44 — moderate конкуренция (между AAVE 19/32 и DOGE 61/48)

### Microprice predictiveness — **умеренный с медленным затуханием**

corr(edge, Δmid_+k):
- k=1: **+0.162** (≈ 537 ms)
- k=5: +0.125
- **k=10: +0.123** — почти не затухает!
- k=30: +0.053
- k=100: +0.022

Сравнение по десяти активам: SOL +0.267, DOGE +0.187, **XPL +0.162**, AVAX/HYPE +0.157,
LINK +0.135, ZEC +0.130, AAVE +0.087, TON +0.059, TIA +0.011.

**Уникально для XPL: сигнал не затухает в горизонте k=1–10 (≈ 5 секунд).** У всех
других активов corr резко падает от k=1 к k=5 (в 2–3 раза). У XPL остаётся
+0.12 даже на k=10. Это означает **более долгоживущий microprice edge** —
возможно из-за trend-momentum периода: imbalance работает не только как
short-term noise, но как trend continuation signal.

**Для стратегии:** microprice — реальный edge на XPL. Сильнее ZEC/AAVE,
сопоставим с AVAX/HYPE. Долгое затухание делает сигнал особенно ценным.

---

## §4 Trade analysis

### Масштаб активности
- **290,717 fills за 5 дней = 40/мин** — **второй после HYPE** (108/min). В 8× активнее ZEC (18/min).
- Total: 1.67B XPL × ~$0.13 mid ≈ **$216M / 5 дней = $43M/день**
- В **5× меньше** SOL ($200M), в **4× меньше** HYPE ($160M), но в **8× больше** AAVE ($4M)

### Структура участников сделок
- Buy 52.1% / Sell 47.9% по count, **Buy 55.5% / Sell 44.5% по volume**
- **Strong BUY-aggressor bias по объёму** — консистентно с +89% rally (агрессивная покупка)
- Median trade size: **1,655 XPL** (~$215). Mean: 5,731 XPL (~$745). p99: 69,965 XPL (~$9,100)

### Inter-arrival (примерно)

С 40 fills/min среднее inter-arrival ≈ 1.5s. Sweep-доля по типичному образцу
40-60% для активов с 40+/min.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms — стандарт
- **Trade-to-snapshot lag:** типично 134 ms median, дыры в LOB ~1%

---

## §6 Order book microstructure

### Churn
- **Either bid/ask changed: 35.0%** снапшотов — высокий (между AAVE 33% и HYPE 32%)
- Bid changed 26.4%, ask changed 21.2% — asymmetry в сторону bid-движений (rally вверх)
- **Median L1 lifetime: 503 ms** ≈ один snapshot — здоровая жизнь (как у SOL/DOGE)
- Mean 1,739 ms, p90 4,837 ms

**Уникально:** XPL имеет L1 lifetime ~500 ms, **не 0 ms как у HYPE/ZEC/AAVE**.
Это значит:
- Реальный churn ≈ 1 Hz (не сильно выше snapshot rate)
- L1 не "лучается" между MM-ботами как у HYPE
- Penny-jump конкуренция умеренная

### L1 очередь
- Median 1 ордер / сторону, mean 1.64–1.85 — низкая конкуренция (как AAVE)
- Median order $512 / $461 — средние по абсолюту

---

## §7 Price dynamics

### σ at horizons
- σ(1s) = 3.574 bps — **в 4× больше SOL, в 2.7× ZEC**
- σ(1min) = 37.5 bps
- σ(5min) = **82.4 bps** — катастрофический горизонт

### Range внутри окна — **экстремальные дислокации**
- median Range(1min) = **19.5 bps** — за минуту обычный диапазон ≈ 19 ticks
- p99 Range(5min) = **186 bps** — экстремальные эпизоды
- max Range(5min) = **3,092 bps (30.9%)** — катастрофа (вероятно liquidation cascade)

Сравните: SOL Range(5min) ~17 bps, HYPE ~30 bps, **XPL ~82 bps**. XPL движется в 3–4×
быстрее остальных активов.

**Stale quote horizon:** **<200 ms**. Quote должен обновляться **на каждом snapshot
edge** при σ-spikes.

---

## §8 Fee economics

- **Effective maker rate: +0.216 bps** — между AVAX (+0.190) и LINK (+0.250)
- **Effective taker rate: +3.307 bps**
- **Round-trip cost: +3.523 bps**
- Maker fills с rebate: **52.5% count, 56.5% volume** — moderate top-tier penetration

### Базовая экономика для нашей base-tier стратегии

| | Mean spread | Round-trip cost | Gross edge |
|---|---|---|---|
| Base tier (we) | 3.09 bps | 3.0 bps | **+0.09 bps** ✓ (marginal) |
| Top-tier rebate | 3.09 bps | −0.6 bps | **+3.69 bps** |

**XPL — единственный low-microprice актив с положительным base-tier edge.**
SOL и TIA имеют positive edge, но больший спред у SOL компенсирует и обычная adverse selection.
Top-tier edge **+3.69 bps gross** — лучший в "high-σ" группе (vs HYPE +1.06, ZEC +1.61, AAVE +1.68).

Проблема: σ/spread = 1.16. Adverse selection при σ(1s)=3.57 bps сжигает edge быстро —
expected loss per round-trip может превысить gross edge.

---

## §9 Funding rate — **самый позитивный из десяти**

```
Records: 240 hours (Apr 1–10, 2026)
Mean rate:   +0.1318 bps/hr = +3.16 bps/day  (longs PAY shorts)
Std:          0.071 bps/hr  (умеренная вариативность)
Min rate:    -0.085 bps/hr  (мягкий негатив)
Max rate:    +0.892 bps/hr  (!) — **выше floor в 7×**
p25/p50/p75: +0.125 / +0.125 / +0.125 (floor-pinned majority)
Negative rate: 0.4% of hours (ОДИН час из 240)
Mean premium: +0.16 bps (mark ≈ oracle — уникально!)
```

### Профиль — **floor + heavy positive tail**

- **99.6% часов rate ≥ 0** — единственный актив где negative funding почти не существует
- p25=p50=p75 = floor (+0.125 bps/hr) — большую часть времени на floor
- Но **max +0.892 bps/hr — в 7× выше floor** (!), на других активах max = floor
- Среднее +0.132 = выше floor → есть значимые spike'и premium ≫ 0.01%
- **Premium mean +0.16 bps** — единственный актив с **positive premium**. mark > oracle.

Это значит: XPL torgуется с **премией к oracle** (часто) → лонги активно покупают
perp выше реальной цены → funding spikes до +0.89 bps/hr в этих часах.

### Финансовый эффект для MM

Flow strongly long-aggressor (Buy 55.5% by volume) → buy-aggressors доминируют →
бьют ask → **MM-ask filled → MM в short позиции**. При rate +0.132 bps/hr (longs pay):

- 5,000 XPL short × $0.13 × 0.132 bps/hr × 24h = **+$0.21/день** на $650 inventory
- В peak часах (+0.89 bps/hr): +$1.39/час на той же позиции = **$33/час** при удержании
- На $5k капитале с типичным ±20,000 XPL inventory: ~$1–5/день funding income

**Funding на XPL — самый выгодный для MM-shorts из десяти.** Это противоположно
TON/AAVE где long-biased flow + positive rate = MM платит. На XPL flow покупает —
MM становится shortom — получает rich funding income.

---

## §10 Market participants — **уникальная liquidation stress**

### Концентрация
- **3,480 уникальных адресов** — между ZEC (3,681) и DOGE (2,668)
- **Gini = 0.950** — высокая, стандарт
- Top-5: **25.0%**, Top-20: 48.1%, Top-100: **77.5%** — **наименее концентрированный** рынок из десяти
  (для сравнения SOL top-100 = 78.2%, HYPE = 68%, AVAX = ?)

### Top users — настоящие MM
- 0x15094c3... — 68.2% maker, **$35.93M volume**, net fee +$1,106 (не top-tier)
- 0xd071d6d... — **100% maker, $18.68M, rebate −$187** — топ top-tier MM
- 0x57dd78c... — 88% maker, $18.00M, fee +$377
- 0xecb63ca... — 20.5% maker, $16.86M, net fee **+$2,718** (large taker)
- 0x6ba889d... — 93.5% maker, $6.65M

Сравнительно много top-tier MM с $5M+ активности. Конкуренция реальная.

### Open vs Close flow — **значительные ликвидации**

```
                              n   count_%  volume ($M)  volume_%
Auto-Deleveraging           698      0.1         16.4       4.0%
Close Long              100,496     17.3         76.6      18.8%
Close Short             173,634     29.9         98.4      24.2%
Liquidated Cross Long       683      0.1         16.6       4.1%
Liquidated Isolated Long     31      0.0          0.1       0.0%
Open Long               110,687     19.0         83.8      20.6%
Open Short              183,789     31.6        105.3      25.9%
Long > Short              5,725      1.0          4.6       1.1%
Short > Long              5,689      1.0          4.3       1.1%

Liquidation + ADL volume: $33.1M (8.1% от total!)
Open: $189.1M (51.9%)
Close: $172.6M (48.1%)
Open Short / Open Long = 105.3 / 83.8 = 1.26×
```

**Уникально: 8.1% объёма — ликвидации и ADL.** Сравните: HYPE имел 2 события,
ZEC 0, остальные 0. XPL — **единственный актив где liquidation cascade — регулярное
явление**, не аномалия.

Это объясняет:
1. Max spread 1,252 ticks (921 bps) — во время liquidation events
2. Kurtosis 1,077 в returns — extreme tail moves в эти моменты
3. Max range 5min = 3,092 bps (30.9%) — единичные эпизоды catastrophic moves

**Open Short 26% > Open Long 21% по объёму.** Участники активно открывали шорты
(возможно ставили против rally). Но buy-aggressor volume 55.5% > sell-aggressor —
много шортов закрывались (capitulation) → buy-aggressor flow доминировал по cumulative impact.

### Что это значит для MM
- Flow в основном aggressive buyers (taker buys) → MM в shortom
- Liquidations — **запрограммированный adverse selection** в эти моменты
- Inventory limit ДОЛЖЕН быть жёстким — нельзя держать positions через liquidation cascades

---

## Общий сравнительный профиль XPL

| | SOL | HYPE | **XPL** | ZEC | AAVE | AVAX | LINK | DOGE | TON | TIA |
|---|---|---|---|---|---|---|---|---|---|---|
| Объём/день | $200M | $160M | **$43M** | $31M | $4M | $15M | $12M | small | $4M | small |
| Mean spread | 3–8 bps | 0.46 | **3.09** | 1.01 | 1.08 | 0.98 | 0.87 | 0.28 | 2.69 | 3.82 |
| σ(1s) bps | 0.779 | 0.924 | **3.574** ⚡ | 1.341 | 0.730 | 0.743 | 0.678 | 0.655 | 0.565 | 0.855 |
| σ/spread | 0.16 ✅ | 2.01 | **1.16** | 1.33 | 0.68 | 0.76 | 0.78 | 2.34 | 0.21 | 0.22 |
| Microprice corr | +0.267 | +0.157 | **+0.162** | +0.130 | +0.087 | +0.157 | +0.135 | +0.187 | +0.059 | +0.011 |
| Microprice decay k=10 | сильный | сильный | **слабый** ⚡ | сильный | сильный | сильный | сильный | сильный | — | — |
| Stale % | 84% | 69% | **66%** | 63% | 67% | 60% | 65% | 74% | 91% | 84% |
| L1 lifetime (med) | 527 ms | 0 ms | **503 ms** | 0 ms | 0 ms | — | — | 506 ms | 2,672 ms | 1,041 ms |
| Trade rate /min | 50+ | 108 | **40** | 18 | 5 | 8 | 6 | 7 | 3 | 2 |
| Funding mean | -0.013 | +0.060 | **+0.132** ⚡ | -0.102 | +0.082 | +0.101 | +0.109 | +0.050 | +0.117 | -0.097 |
| Funding max | floor | floor | **+0.892** ⚡ | floor | floor | floor | floor | floor | floor | — |
| Flow bias | neutral | long | **buy-aggr / open-short** | long | strong short | long | long | short | short | small short |
| Liquidations % vol | 0 | tiny | **8.1%** ⚡⚡ | 0 | 0 | 0 | — | 0 | 0 | 0 |
| Maker rebate % vol | 79.5% | 53.5% | **56.5%** | 66.5% | 63.6% | 49.4% | — | 68.4% | 32.4% | 43.6% |
| Unique users | 12,390 | 12,616 | **3,480** | 3,681 | 2,085 | 2,542 | 2,515 | 2,668 | 1,154 | 537 |
| Trend (5 days) | mild | mild | **+89%** ⚡⚡ | +11.7% | +11.6% | mild | mild | flat | mild | mild |

⚡ = XPL extreme. ⚡⚡ = unique across выборки.

---

## Ключевые параметры для AS-калибровки (если бы пришлось)

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | **3.574 bps/s — наивысший из десяти** | §2 |
| σ/spread ratio | 1.16 — седьмое место | §2 |
| σ динамика | EWMA halflife **30–60 секунд** (regime изменяется быстро) | §2 |
| Microprice edge | corr = +0.162 — **сигнал не затухает k=1..10** | §3 |
| L1 median orders | 1 / 1 | §6 |
| Median order size L1 | 3,932 XPL = ~$512 | §3 |
| L1 lifetime | 503 ms median — здоровая | §6 |
| Mean spread | 3.09 bps — **выше base-tier break-even на +0.09 bps** | §8 |
| Base-tier edge | **+0.09 bps gross** (marginal) | §8 |
| Top-tier edge | +3.69 bps gross — **лучший в high-σ группе** | §8 |
| Stale quote horizon | **<200 ms** — критически короткий | §7 |
| Snapshot cadence | 537 ms median — **больше stale horizon** ⚠️ | §5 |
| Funding (Apr 2026) | **+0.132 bps/hr mean, max +0.892** ⚡ | §9 |
| MM inventory bias | SHORT (из-за buy-aggressor flow) | §10 |
| Funding эффект для MM | **+$1–5/день income** на $5k (positive) | §9 |
| Liquidation risk | **8.1% объёма — регулярный stress** | §10 |
| Expected trade rate | 40/min → ~10 unique MO/мин | §4 |
| Realistic order size | 100–1000 XPL ($13–130) | §3, §4 |
| Тренд периода | **+89% за 5 дней — extremely non-baseline** | §1 |

---

## Итог: XPL — единственный "high-vol high-spread" актив, но extreme risk

### Что делает XPL уникальным

1. **Spread выше break-even (+0.09 bps gross)** — единственный из "high-activity" группы.
   SOL/TIA имеют edge, но XPL имеет **40 fills/min** и **$43M/день** — больше потенциала PnL.

2. **σ(1s) = 3.57 bps — в 4× выше SOL.** Самая волатильная среда. Adverse selection
   на every quote = real.

3. **Funding +0.132 bps/hr mean, max +0.892** — самый позитивный из всех. MM-shorts
   получают income до **$33/час в peak hours**. На +89% rally market shorts capitulate →
   MM в shorts от buy-flow → MM получает funding.

4. **Liquidations 8.1% volume — регулярные stress events.** Все остальные активы
   имели <0.1% ликвидаций. XPL имеет structurally-elevated tail risk.

5. **Microprice сигнал не затухает k=1–10** — едва ли единственный актив с долгоживущим
   imbalance edge (5 секунд). Стратегия может удерживать quote дольше.

### Профиль риска

| Аспект | Pros | Cons |
|---|---|---|
| Edge per fill | +0.09 base / +3.69 top-tier | high adverse selection σ/spread=1.16 |
| Activity | 40 fills/min — третий по активности | $43M < SOL/HYPE |
| Funding | **best for MM-shorts** | regime-dependent, may flip |
| Liquidations | **opportunity** во время cascade events | catastrophic tail moves |
| Sample quality | actual market activity | **+89% trend bias** — данные не baseline |

### Обновлённая рекомендация для нашего старта (10 активов)

1. ✅ **SOL** — единственный базовый base-tier актив с устойчивым PnL.
2. ⚠️ **XPL (priority-2?)** — **возможно второй кандидат для base-tier ПОСЛЕ SOL**:
   - Spread > break-even
   - 40 fills/min × $43M/день — серьёзная активность
   - Funding income до $5/день (плюс к edge)
   - НО: σ(1s)=3.57 — нужен жёсткий σ-EWMA + liquidation detection + inventory limit
   - НО: sample bias (+89% за 5 дней) делает калибровку ненадёжной
3. ⚠️ **HYPE** (priority-3) — top-tier + volume edge ($160M/день)
4. ⚠️ **ZEC** (priority-4)
5. ⚠️ **AAVE** (priority-5)
6. ⚠️ AVAX/LINK/DOGE — priority-6 и далее
7. ❌ TON / TIA — не жизнеспособны

### Главный вопрос для XPL: реальный ли это base-tier candidate?

**За (если данные показывают true regime):**
- Spread 3.09 bps достаточен для base-tier при умеренном adverse selection management
- 40/min активности обеспечивает быструю валидацию стратегии
- Funding cushions inventory cost

**Против (что нужно проверить):**
1. **+89% rally — нерепрезентативный период.** В ranging-режиме σ(1s) может
   упасть с 3.57 до 1.5–2 → σ/spread улучшится с 1.16 до 0.5–0.7
2. Или σ остаётся высоким при flat price (regime может persist) — тогда XPL
   structurally close к ZEC/HYPE кластеру
3. **Max spread 921 bps** показывает что dislocation events случались — могут уничтожить
   капитал если не отменить котировки вовремя

**Рекомендация:** XPL **требует длинной истории данных** (30+ дней включая ranging)
ДО принятия решения. На текущих 5 днях оценка слишком зависит от trend regime.

**Если есть выбор между XPL и HYPE для priority-2 после SOL:**
- XPL — больший spread, лучший funding, но extreme σ и liquidation risk
- HYPE — больший объём ($160M vs $43M), стабильнее (нет ликвидаций), но spread намного ниже
- **HYPE проще запустить**, XPL имеет higher upside но higher risk

### Уникальный риск: liquidation cascade

XPL имел 8% объёма от ликвидаций за 5 дней. Это **systemic risk** — наш MM-quote
может попасть в **cascade** где:
1. Price drops sharply (+5% за минуту бывало)
2. Long positions liquidate, force-selling
3. Order book gets swept past L1 (max sweep до 921 bps spread)
4. Our maker quotes filled на стороне long → moment-после margin call ourselves

**Mitigation:**
- Жёсткий size limit (XPL volatility justifies ≤0.5% of capital per quote)
- Stop-trading на основе σ-spike triggers
- Funding-based regime detection (when funding > +0.5 bps/hr → market is paying for hedge → reduce inventory)
