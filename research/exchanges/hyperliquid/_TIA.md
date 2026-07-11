# TIA-USDC Perp — Main Findings
**Данные:** Apr 1–5, 2026 · 5 дней · LOB + trades · TICK = $0.00001
**Цена:** $0.28–$0.31

---

## §1 General statistics

- LOB: 778,396 снапшотов, медианный интервал **537 ms** (идентично SOL)
- Trades: 15,596 taker fills за 5 дней → **0.04/sec (2/min)**
- Mean spread: **11.09 ticks (3.82 bps)**
- Maker fills с rebate: **51.4%** (vs SOL 69%)

**Для стратегии:** торговая активность в ~20–50× ниже чем SOL на той же бирже. Fills будут редкими — inventory пополняется медленно, каждый fill ценен.

---

## §2 Asset overview

- **Spread:** mean 11 ticks = 3.82 bps, AR(1) = **0.885** (очень персистентный — spread держится часами). p50=11, p99=22 ticks.
- **Возвраты (snapshot-to-snapshot):** stale 84.4%, actual moves std = **1.522 bps** (больше чем SOL 0.779 bps), kurtosis = 20.8
- **σ ∝ √T подтверждено** на всех горизонтах: flat signature plot → random walk.
- **ACF(r) ≈ 0** (random walk), **ACF(r²) значим** (ARCH — кластеризация волатильности).
- σ(1s) = **0.855 bps/s**, σ(5min) = **17.35 bps** — почти идентично SOL (0.779 / 17.4 bps).

**Для стратегии:** EWMA-σ обязателен (ARCH-эффект). Halflife 2–3 мин как для SOL.

---

## §3 Order book structure

- **L1 размер:** bid 2,762 TIA, ask 2,863 TIA. Медиана **1 ордер** на стороне, медианный размер 1,289 TIA.
- **Нетривиально: глубина растёт монотонно** — без "вакуума" L1–L3 как у SOL. L0=2.7k → L10=8.7k → L19=15.3k TIA. Один участник = весь L1.
- **КРИТИЧНО: microprice corr = +0.011** (vs SOL **+0.267**). Imbalance не предсказывает движение mid.

**Для стратегии:** microprice как fair value на TIA не работает — imbalance uninformative. Использовать raw mid + σ-skew без microprice adjustment.

---

## §4 Trade analysis

- **Trade rate: 2/min** — в ~25–50× ниже SOL.
- **Buy/sell:** 44.7% / 55.3%, объём 43.3% / 56.7% — лёгкий sell-bias (согласуется с отрицательным funding).
- **Размер:** mean 408 TIA, median 104 TIA (~$31 при $0.30), p99 = 3,546 TIA.
- **Inter-arrival:** mean Δt = **27.7 s**, median = **12 s**, 51.9% пауз > 10s. Рынок "спит" большую часть времени.
- **Burstiness:** 16.68% событий < 50 ms друг от друга. Когда активен — кластеризован.
- Multi-leg: 15,596 legs → 13,006 уникальных событий (83.4%).

**Для стратегии:** с 2 trade/min ожидай 1–2 фила в каждую сторону в час. Котировки "живут" долго — stale quote риск высокий при любом движении рынка.

---

## §5 Data quality

- **Snapshot cadence:** медиана 537 ms, max gap **404.9 секунды** (больше чем у SOL).
- **Trade-to-snapshot lag:** медиана 134 ms, mean 2,596 ms, p99 = 110,731 ms.

**Для стратегии:** проверка свежести снапшота необходима. Lag > 2s = не котировать.

---

## §6 Order book microstructure

- **Churn:** 15.73% снапшотов — изменение best bid или ask (vs SOL 16.94%).
- **Медианная "жизнь" best price: 1,041 ms** (vs SOL 527 ms) — L1 живёт в **2× дольше**.
- **Depth profile:** монотонный рост. Медиана 1–1.5 ордера на уровне — каждый ордер огромный. L1 avg order = 1,289 TIA, L19 avg = 11,242 TIA.

**Для стратегии:** перекотировать реже чем SOL (~раз в 1–2s). Один cancel крупного игрока = полное обновление L1.

---

## §7 Price dynamics

- **σ(1s) = 0.855 bps/s**, σ(5min) = 17.35 bps. σ ∝ √T подтверждено.
- **Microprice predictiveness = 0.011 на k=1** — фактически ноль на всех горизонтах.
- **Range(5min) median = 6.77 bps** — за 5 мин цена проходит ~1.8 spread. Stale quote = потеря.

**Для стратегии:** microprice не использовать. Stale quote horizon: 2–3s как у SOL.

---

## §8 Fee economics

- **Effective maker rate: +0.151 bps** (vs SOL −0.012 bps). TIA MM-участники net не получают rebate.
- **Effective taker: +2.980 bps**, round-trip: **+3.131 bps**.
- **Maker volume с rebate: 43.6%** (vs SOL 79.5%) — top-tier проникновение значительно ниже.
- Для вас (base tier): maker +1.5 bps, taker +4.5 bps → round-trip = +3.0 bps.

**Для стратегии:** break-even spread > 6 bps с adverse selection. Средний спред 3.82 bps — запас очень мал. Рабочий spread = 5–8 bps.

---

## §9 Funding rate

- **76.7% часов — отрицательная ставка** (шорты платят лонгам) — vs SOL 51%.
- **Mean rate: −0.097 bps/hr = −2.34 bps/day** — по модулю в **7.5× сильнее** чем SOL (−0.013 bps/hr).
- **Premium persistent: −5.76 bps** — TIA-perp торговался с глубоким дисконтом к споту. Отрицательный premium → отрицательный funding → шорты платят лонгам, стимулируя покупки perp.
- **Финансовый эффект:** negative rate = лонги **получают** от шортов. На ±1000 TIA (~$300) income ≈ $0.003/час — пренебрежимо мало по абсолютной величине.

**Для стратегии:** funding — небольшой плюс для long MM (лонги получают), не cost. Добавить `funding_rate × inventory × price` в AS-модель (значение будет положительным при long inventory). Лимит инвентаря ограничивать нужно из-за adverse selection на тонком рынке и редких fills — не из-за funding.

---

## §10 Market participants

- **537 уникальных адресов** (vs SOL 12,390 — в 23× меньше).
- **Gini = 0.895** (vs SOL 0.977 — менее концентрирован).
- Топ-5 = 50.5% объёма; топ-20 = 73.9%; топ-100 = 91.0%.
- **Структура топа разнообразнее:** нет явных pure-maker доминирующих адресов (топ-3 имеют 31–65% maker share). Менее профессиональный рынок.
- **Open ≈ Close (49.8/50.2%)** — сбалансированный flow. Slight short bias в открытиях.

**Для стратегии:** конкурентная среда значительно мягче чем SOL. Но тонкий рынок = выше adverse selection на каждый fill.

---

## Сравнение TIA vs SOL — ключевые различия

| Параметр | TIA | SOL | Вывод |
|---|---|---|---|
| Trade rate | 0.04/sec | ~1–2/sec | SOL в 25–50× ликвиднее |
| σ(1s) | 0.855 bps/s | 0.779 bps/s | Примерно одинаково |
| Mean spread | 3.82 bps | 3–8 bps | Аналогично |
| Microprice corr | **+0.011** | **+0.267** | SOL сигнал в 24× сильнее |
| Funding mean | **−0.097 bps/hr** | −0.013 bps/hr | Оба отрицательные — лонги получают; TIA в 7.5× больше |
| Maker rebate % | 43.6% vol | 79.5% vol | SOL более top-tier |
| Unique users | **537** | 12,390 | TIA конкуренция ниже |
| L1 orders/side | 1 (median) | ~7–8 | TIA книга спартанская |
| L1 lifetime | 1,041 ms | 527 ms | TIA L1 живёт дольше |

---

## Ключевые параметры для AS-калибровки

| Параметр | Значение | Источник |
|---|---|---|
| σ (1s) | 0.855 bps/s | §2 |
| σ динамика | EWMA halflife 2–3 мин | §2 |
| Microprice edge | ≈ 0 — **не использовать** | §3, §7 |
| L1 avg size | 2,762 TIA bid / 2,863 TIA ask | §3 |
| Typical spread | 11 ticks = 3.82 bps | §2 |
| Break-even (base tier) | > 3 bps maker-only, > 6 bps с adverse sel. | §8 |
| Snapshot cadence | 537 ms median | §5 |
| Stale quote horizon | ~2–3s | §6, §7 |
| Funding (Apr 2026) | −0.097 bps/hr (longs earn) | §9 |
| Expected trade rate | 2/min → ~1 fill/сторону в 30 мин | §4 |
| Realistic order size | 50–200 TIA | §3, §10 |
| Max inventory | ±500 TIA (из-за adverse selection на тонком рынке) | §3, §4 |

**Главный вывод:** TIA значительно хуже SOL для MM в данный период по трём осям:
низкая ликвидность (редкие fills) + нулевой microprice сигнал + высокий adverse selection на тонком рынке (один крупный участник = весь L1).
Единственное преимущество — меньше конкуренции (537 vs 12,390 пользователей).
Рекомендация: начинать с SOL, TIA рассматривать позже как диверсификацию.
