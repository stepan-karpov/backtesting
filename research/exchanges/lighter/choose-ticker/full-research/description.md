# Column dictionary — Lighter screening summary

Описание колонок `summary_rows.csv` (полная таблица). Файл генерирует секция 8
ноутбука `research/exchanges/lighter/template.ipynb`: каждый символ апсертит свою
строку (перезапись по `ticker` либо добавление).

`summary_rows_short.csv` — то же, но только колонки, помеченные ниже **★** (основные,
для быстрого сравнения). Порядок колонок в обеих таблицах одинаков.

**Единицы и обозначения**
- **bps** — базисный пункт, 1 bps = 0.01% = 1e-4.
- **$** — USD (quote-валюта); notional сделки = `price × size`.
- **ticks** — в шагах цены (tick size).
- **s / d** — секунды / сутки.
- **share** — доля в диапазоне 0..1.
- **AS drift знаковый:** «+» = цена ушла В сторону агрессора (за покупателем вверх / за продавцом вниз).
- **percentiles:** запись `p{1,5,25,50,75,90,95,99}` означает набор колонок с этими перцентилями (плюс `mean`, `max`).
- ⚠️ **UNVERIFIED** — величина/единицы не подтверждены по `docs/FACTS.md`, выведены эмпирически.

---

## Профиль

| column | unit | meaning |
|---|---|---|
| **★ ticker** | — | Символ актива (ключ строки). |
| **★ ref_price** | $ | Медиана mid-цены за окно — «типичная» цена актива (якорь масштаба, не mark/oracle). |
| book_gaps | count | Число разрывов записи книги (`Δsent_ts` > адаптивного порога, провизорно). QA данных. |

## A — Spread (можем ли котировать)

| column | unit | meaning |
|---|---|---|
| A_tick | $ | ⚠️ Шаг цены (эмпирически из ценовой сетки). |
| A_bps_per_tick | bps | Стоимость одного тика в bps от `ref_price`. |
| A_n_snapshots | count | Число валидных снапшотов LOB. |
| **★ A_spread_ticks_p50** (+ p1..p99, mean, max) | ticks | L1-спред (`ask1−bid1`) в тиках, перцентили. |
| **★ A_spread_bps_p50** (+ p1..p99, mean, max) | bps | L1-спред в bps (`spread/mid·1e4`), перцентили. |
| A_share_spread_eq_1_tick | share | Доля снапшотов со спредом ровно 1 тик. |
| A_share_spread_le_2_ticks | share | Доля со спредом ≤ 2 тика. |
| A_share_spread_ge_5_ticks | share | Доля со спредом ≥ 5 тиков. |

## B — Adverse selection (платит ли после «налога на медлительность»)

Событие = удар тейкера (агрегированные филлы одного ордера). AS(h) = средний знаковый
ход mid через h после удара. Вилка: **hi** — якорь на `timestamp` (матч; импакт не
протекает в m₀, безопасно); **lo** — якорь на `transaction_time` (коммит; нижняя граница).

| column | unit | meaning |
|---|---|---|
| **★ B_as350_hi_bps** | bps | AS на горизонте 350 мс, ветка hi (основная). |
| B_as350_lo_bps | bps | AS на 350 мс, ветка lo (нижняя граница вилки). |
| B_fork_delta350_bps | bps | Ширина вилки на 350 мс (`hi − lo`). |
| B_as1s_hi_bps | bps | AS на 1 с (hi). |
| B_as10s_hi_bps | bps | AS на 10 с (hi). |
| B_halfspread_p50_tw_bps | bps | Медианный полуспред, time-weighted (взвешен по времени). |
| **★ B_edge_bps** | bps | Edge = `halfspread_p50 − AS350_hi` (сколько остаётся мейкеру после adverse selection). |
| B_n_events | count | Число событий с валидным m₀. |
| B_valid_m0_share | share | Доля событий с валидным m₀. |
| B_negative_lag_share_commit | share | QA: доля отрицательных лагов импакт-батча при старом якоре (мера «боли» от коммит-якоря). |

## C — Volume (кормит ли поток)

| column | unit | meaning |
|---|---|---|
| **★ C_n_trades** | count | Число филлов за окно. |
| **★ C_trades_per_day** | count/d | Филлов в сутки (нормировка на окно). |
| C_base_volume_total | base coin | Суммарный объём в базовой монете. |
| C_notional_total_usd | $ | Суммарный notional за окно. |
| **★ C_notional_per_day_usd** | $/d | Notional в сутки (экстраполяция с неполного окна). |
| C_trade_usd_p50 (+ p1..p99, mean, max) | $ | Notional на сделку, перцентили. |
| C_taker_buy_share_count | share | Доля филлов с агрессором-покупателем (по числу). |
| C_taker_buy_share_notional | share | То же по $. |

## D — Sweep (хищный ли поток)

Свип = тейкер-ордер, пробивший ≥2 ценовых уровня в пределах одного блока.
`algo_twap` — ордера, размазанные по >1 блоку (медленное исполнение, вынесены отдельно).

| column | unit | meaning |
|---|---|---|
| D_n_taker_orders | count | Число реконструированных тейкер-ордеров. |
| **★ D_sweep_share_notional** | share | Доля тейкер-$ в свипах (основная метрика D). |
| D_sweep_share_count | share | Доля свипов по числу ордеров. |
| D_sweep_share_notional_acct_block | share | Верхняя граница: группировка по `(account, block)` (против дробления IOC). |
| D_algo_twap_share_notional | share | Доля тейкер-$ в algo/twap-подобных ордерах. |
| D_liq_share_notional | share | Доля тейкер-$ в ликвидациях. |
| D_sweep_share_notional_buy | share | Sweep-доля внутри покупок-агрессий. |
| D_sweep_share_notional_sell | share | Sweep-доля внутри продаж-агрессий. |
| D_sweep_depth_bps_p50 / _p90 | bps | Глубина свипа (`(max−min)/mean·1e4`), перцентили. |
| D_sweep_levels_p50 / _p90 | count | Число разных ценовых уровней в свипе. |
| D_legs_p50 / _p90 / _p99 | count | Число филлов на тейкер-ордер, перцентили. |
| D_legs_max | count | Макс. число филлов на тейкер-ордер. |

## E — Jumps (часты ли резкие движения)

Рывок = размах mid (`max−min`) внутри неперекрывающегося 1-с бина.

| column | unit | meaning |
|---|---|---|
| **★ E_obs_days** | d | Длина окна наблюдения. |
| E_seconds_observed | count | Число 1-с бинов. |
| **★ E_jumps_gt20bps_per_day** | count/d | Рывков >20 bps/1 с в сутки (основная метрика E). |
| E_jumps_gt50bps_per_day | count/d | Рывков >50 bps/1 с в сутки. |
| E_max_1s_move_bps | bps | Наибольший 1-с размах mid. |
| E_range_bps_p99 | bps | p99 распределения 1-с размахов. |

## F — Competition (занято ли место)

Конкурент = аккаунт-мейкер (пассивная сторона). Системные `account_id` (~2⁴⁸:
ликвидатор/страховой фонд) вынесены отдельно.

| column | unit | meaning |
|---|---|---|
| F_n_makers | count | Число уникальных пользовательских мейкер-аккаунтов. |
| F_n_makers_gt1pct | count | Мейкеров с долей >1% maker-объёма. |
| **★ F_top1_maker_share** | share | Доля топ-1 мейкера в maker-объёме (доминирование). |
| F_top3_maker_share | share | Доля топ-3 мейкеров. |
| F_maker_hhi | index | Индекс Херфиндаля концентрации мейкеров (0..1). |
| F_top1_maker_purity | share | «Чистота» топ-1: его maker-доля в собственном обороте (MM ли, а не directional). |
| F_system_maker_share | share | Доля maker-объёма от системных аккаунтов. |
| F_premium_tier_share | share | ⚠️ Доля maker-объёма на лучшем тире `maker_fee` (сигнатура топ-tier MM; единицы UNVERIFIED). |
| F_n_fee_tiers | count | Число различных тиров `maker_fee`. |
| **★ F_l1_requote_p50_s** | s | Медианный интервал между сменами best_bid/ask (реакция тача). |
| F_l1_requote_p90_s | s | p90 того же интервала. |

## G — Touch depth (глубина тача vs наш ордер)

Сколько $ ликвидности стоит на лучшем уровне (L1) — определяет нашу долю очереди
против ордера `ORDER_USD` (по умолчанию $500, не инвентарный кап). Перцентили
time-weighted. ⚠️ `queue_share` — **прокси** (статическое отношение размеров), не
реальный fill-share: тот зависит от FIFO-приоритета и распределения размеров сделок →
считается в replay. Читать **в паре со спред-режимом (A)**: при тугом спреде —
join-очередь; при широком — котируем внутрь, тач менее релевантен.

| column | unit | meaning |
|---|---|---|
| G_order_usd | $ | Размер нашего ордера, относительно которого считается доля очереди. |
| G_touch_bid_usd_p25 / _p50 / _p75 | $ | Глубина тача на биде (L1), time-weighted перцентили. |
| G_touch_ask_usd_p25 / _p50 / _p75 | $ | То же на аске. |
| **★ G_touch_usd_p50** | $ | Глубина тача (среднее бид/аск), медиана. |
| **★ G_queue_share_p50** | share | ⚠️ Наша доля очереди при `ORDER_USD` на p50-глубине (прокси): `ORDER_USD/(depth+ORDER_USD)`. |
