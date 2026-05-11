# AVAX-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.0001
**Цена:** $8.62–$9.48

---

## §1 General statistics

- LOB: 778,469 снапшотов, медианный интервал **537 ms**
- Trades: 55,427 taker fills за 5 дней → **0.13/sec (8/min)**
- Mean spread: **8.75 ticks = 0.98 bps** — НИЖЕ break-even базовой комиссии!
- Maker fills с rebate: **42.2%** (наименьший из трёх активов)

**Для стратегии:** ликвидность умеренная (между TIA и SOL), но mean spread 0.98 bps структурно недостаточен для base-tier MM.

---

## §2 Asset overview

- **Spread:** mean 0.98 bps, AR(1) = **+0.670**. p50=8, p75=12, p99=27 ticks. Skewness +3.20, kurtosis +80.
- **13.13% времени — spread = 1 tick ($0.0001 = 0.11 bps)** — рынок очень часто в минимальном спреде.
- **Stale (Δmid=0): 60.6%** — значительно ниже SOL/TIA (84%). Цена двигается чаще.
- **Actual moves:** 306,991 событий, std = **0.787 bps**, kurtosis = **156.9** (fat tails).
- **p50 move = 3 ticks, p99 = 28 ticks**.
- **ACF(r) ≈ 0, ACF(r²) значим** — random walk + ARCH.
- σ(1s) = **0.743 bps/s**, σ(5min) = **16.59 bps**.

**Signature plot:** небольшой upslope 0.743 (1s) → 0.962 (30s) — нет mean reversion, лёгкое momentum.

**Для стратегии:** EWMA-σ обязателен, halflife 2–3 мин.

---

## §3 Order book structure

- **L1 размер:** bid 372 AVAX, ask 338 AVAX. Медиана **1 ордер** на стороне, median order size **120 AVAX bid / 111 AVAX ask**.
- **Нетривиально: depth profile почти плоский.** L0=372 → L1=315 (небольшой дип) → плато ~500 AVAX с L7+. Нет ни "вакуума" как у SOL, ни монотонного роста как у TIA. Ликвидность равномерно распределена по глубине.
- **Microprice corr = +0.157** (vs SOL +0.267, TIA +0.011) — работающий сигнал, средний.

**Для стратегии:** microprice использовать как компонент fair value с умеренным весом. Плоская книга = стабильное adverse selection без острых зон риска.

---

## §4 Trade analysis

- **Trade rate: 8/min** — между TIA (2/min) и SOL.
- **Buy/sell: 51.1% / 48.9%** — почти идеальный баланс. По объёму: buy 47.4%, sell 52.6%.
- **Размер:** mean 45 AVAX, median **8.9 AVAX** (~$80), p99 = 562 AVAX. Типичный fill мелкий.
- **Inter-arrival:** mean Δt = **7.8 s**, median = **1.1 s** — заметно активнее TIA.
- **30.73% событий < 50 ms** — высокая burst-кластеризация.
- **Multi-leg: 55,427 legs → 38,461 unique events = 69.4%** — наивысший sweep-ratio из трёх. Каждый третий событие — multi-leg sweep.
- 22.4% пауз > 10s — рынок заметно активнее TIA.

**Для стратегии:** 30.7% буrstов < 50 ms + высокий sweep ratio = агрессивные MO частые. Быстрая отмена при детекции sweep обязательна.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, max gap 404.4 с.
- **Trade-to-snapshot lag:** медиана 134 ms, mean 2,139 ms, p99 = 97,781 ms.

---

## §6 Order book microstructure

- **Churn: 39.95% снапшотов — изменение best bid или ask** — в **2.5× больше чем SOL (16.94%)** и TIA (15.73%)!
- **Bid changed: 29.45%, ask changed: 24.18%** — обе стороны высокоактивны.
- **Медианная "жизнь" best price: 0 ms** (vs SOL 527 ms, TIA 1,041 ms). L1 меняется быстрее snapshot cadence — реальный lifetime < 537 ms. Mean = 1,476 ms.
- Самый быстро-меняющийся ToB из трёх активов.
- Trade depth: большинство fills на L1 (depth=0).

**Для стратегии:** перекотировать на каждый snapshot (~537ms). При HL latency 200ms — реалистично, но нужен надёжный WS-фид без пропусков.

---

## §7 Price dynamics

- **σ(1s) = 0.743 bps/s** — наименьший из трёх.
- **σ(5min) = 16.59 bps**. σ ∝ √T подтверждено.
- **Microprice corr = +0.157** на k=1, +0.104 на k=5 — постепенное затухание.
- **Range(5min) median = 6.22 bps** — за 5 мин цена проходит ~6.3 spread'а.

**Для стратегии:** stale quote horizon ~2s (быстрее чем для SOL/TIA из-за высокого churn).

---

## §8 Fee economics — КРИТИЧЕСКИЙ БЛОКЕР

- **Effective maker rate: +0.190 bps** (vs SOL −0.012, TIA +0.151) — хуже обоих из сравниваемых трёх активов.
- **Effective taker: +3.148 bps**, round-trip: **+3.338 bps**.
- **Mean spread 0.98 bps < break-even 3.0 bps** — структурный дефицит **2 bps на каждый round-trip**.

**Расчёт:** при среднем spread 0.98 bps на base tier:
- Maker fee = +1.5 bps × 2 = 3.0 bps
- Gross spread = 0.98 bps
- PnL = **−2.02 bps** даже при нулевом adverse selection

**Это рынок для top-tier.** С rebate −0.3 bps:
- PnL = 0.98 − (−0.6) = **+1.58 bps gross** per round-trip

**Для стратегии:** при текущем spread на AVAX котировать убыточно на base tier. Переходить на AVAX только после достижения top-tier объёма.

---

## §9 Funding rate — умеренный cost для лонгов

- **Только 8.3% часов — отрицательная ставка** (vs SOL 51%, TIA 76.7%).
- **Mean rate: +0.101 bps/hr = +2.43 bps/day** — почти постоянно на floor бычьего рынка.
- p50 = **0.125 bps/hr** — ставка большую часть времени у нормального floor.
- Лонг в AVAX **платит** funding. На +100 AVAX за 240 часов: **−$21.7 USDC**.

**Причина:** AVAX-perp без скидки к споту, premium ≈ 0. Funding по формуле = floor 0.01%/8h → лонги платят шортам даже при нулевой премии.

**Для стратегии:** positive rate = лонги ПЛАТЯТ шортам. MM, оставшийся net long из-за short bias контрагентов, несёт −$2/день на $900 inventory. Добавить в AS-модель как inventory cost.

---

## §10 Market participants

- **2,542 уникальных адресов** (между TIA 537 и SOL 12,390).
- **Gini = 0.956** — высокая концентрация.
- Топ-5 = 37.3%; топ-20 = 65.0%; топ-100 = 86.1%.
- **Крупнейший участник: $7.68M notional** за 5 дней при 22% maker share — directional trader.
- **Нетривиально: выраженный short bias.** Open Short 31.4% vs Open Long 16.8% (2:1). По объёму: Short 33% vs Long 15%. Шорт-позиции открываются в 2× чаще лонгов.
- Open ≈ Close (49.5/50.5%) — сбалансировано, нет накопленного дисбаланса.
- Есть чёткие pure-maker адреса (100% maker) и pure-taker (0% maker).

**Для стратегии:** strong short bias = типичный контрагент MM открывает AVAX как шорт. Это оставляет MM net long. При позитивном funding (лонги платят) это дополнительный cost для MM. Inventory cost = adverse selection + funding.

---

## Итоговое сравнение трёх активов

| Параметр | AVAX | TIA | SOL |
|---|---|---|---|
| Trade rate | 8/min | 2/min | ~50+/min |
| σ(1s) | 0.743 bps/s | 0.855 bps/s | 0.779 bps/s |
| Mean spread | **0.98 bps** | 3.82 bps | 3–8 bps |
| Spread vs break-even | **−2 bps (убыток!)** | +0.82 bps (едва) | 0–5 bps ✓ |
| Microprice corr | +0.157 | +0.011 | **+0.267** |
| Funding mean | **+0.101 bps/hr** | −0.097 bps/hr | −0.013 bps/hr |
| Churn rate | **39.95%** | 15.73% | 16.94% |
| L1 lifetime median | ~0 ms | 1,041 ms | 527 ms |
| Maker rebate vol% | 50.4% | 43.6% | **79.5%** |
| Unique users | 2,542 | 537 | 12,390 |
| Priority для base-tier | ❌ spread < break-even | ⚠️ tiny margin | ✅ рабочий |

---

## Ключевые параметры

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.743 bps/s | §2 |
| Microprice edge | corr = +0.157 | §3 |
| L1 avg size | 372 AVAX bid / 338 AVAX ask | §3 |
| Mean spread | 8.75 ticks = 0.98 bps | §2 |
| Break-even (base tier) | > 3 bps — рынок структурно убыточен | §8 |
| Funding (Apr 2026) | +0.101 bps/hr (longs pay) | §9 |
| L1 churn | 39.95% / снапшот | §6 |
| Stale quote horizon | ~2s | §6, §7 |

**Итог:** AVAX при текущем spread непригоден для base-tier MM.
SOL — единственный рабочий вариант из трёх для старта.
