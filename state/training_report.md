# Training report — 2026-11-22 10:52 IST

Data 2018-11-20 → 2026-11-20. Training/evaluation years 2021-05-20 → 2025-11-20; **holdout (never used for choices) 2025-11-20 → 2026-11-20**.

Usable factors: base 19, macro 15, sector 4, news 6, world 8, finbert 0

## Decision: kept current model **champion: price+world · P2**

News-exit rule: **off**

## Portfolio backtests (₹10,000, real costs)

| Setup | Train return | Train Sharpe | Holdout return | NIFTY (holdout) | Holdout Sharpe | Holdout max DD | OOS IC |
|---|---|---|---|---|---|---|---|
| champion: price+world · P2 | +240.5% | 1.36 | +9.6% | -1.5% | 0.64 | -17.15% | 0.0351 |
| everything · P2 | +107.9% | 0.92 | -9.0% | -1.5% | -0.54 | -16.11% | 0.0462 |
| price+macro+sector · P3 | +189.9% | 1.28 | -8.0% | -1.5% | -0.4 | -16.76% | 0.0373 |
| price+macro+sector · P2 | +199.3% | 1.3 | -13.0% | -1.5% | -0.79 | -17.81% | 0.0363 |

## Walk-forward out-of-sample skill (training years, refit quarterly)

IC = rank correlation between the model's scores and next-month excess returns (0 = no skill; 0.03–0.08 is useful in practice).

| Setup | OOS IC | t-stat | Top-3 picks' excess return / month | Months |
|---|---|---|---|---|
| everything · P2 | 0.0462 | 1.86 | -0.05% | 52 |
| price+macro+sector · P3 | 0.0373 | 1.65 | -0.48% | 52 |
| price+macro+sector · P2 | 0.0363 | 1.50 | +0.14% | 52 |
| price+macro · P2 | 0.0353 | 1.44 | +0.11% | 52 |
| everything · P3 | 0.0334 | 1.39 | +0.57% | 52 |
| everything · P1 | 0.0309 | 1.27 | +0.85% | 52 |
| price+macro+sector · P1 | 0.0299 | 1.22 | +0.15% | 52 |
| price+macro · P1 | 0.0256 | 1.04 | +0.74% | 52 |
| price+sector · P1 | 0.0253 | 0.91 | +0.40% | 52 |
| price+macro+sector+news · P1 | 0.0227 | 0.92 | +0.83% | 52 |
| price+world · P1 | 0.0212 | 0.81 | +0.32% | 52 |
| price · P1 | 0.0205 | 0.73 | +0.87% | 52 |
| price+macro · P3 | 0.0176 | 0.72 | +0.73% | 52 |
| price+news · P1 | 0.0142 | 0.51 | +0.59% | 52 |

## Factor tests (monthly IC vs next-month excess return)

|t| ≥ 2 is roughly 'statistically significant'. Holdout column shows whether the effect held up in the unseen year.

| Factor | Group | IC (train) | t (train) | % months positive | IC (holdout) |
|---|---|---|---|---|---|
| rsi_14 | base | -0.0614 | -2.34 | 40% | -0.0322 |
| drawdown_252 | base | -0.0655 | -2.14 | 35% | -0.0264 |
| dist_sma50 | base | -0.0547 | -1.92 | 37% | -0.0390 |
| rel_sector_63 | sector | -0.0419 | -1.82 | 46% | -0.0096 |
| rank_ret_21 | base | -0.0447 | -1.69 | 46% | -0.0884 |
| ret_21 | base | -0.0447 | -1.69 | 46% | -0.0884 |
| rel_sector_21 | sector | -0.0326 | -1.41 | 38% | -0.0451 |
| ret_63 | base | -0.0429 | -1.31 | 46% | -0.0712 |
| rank_ret_63 | base | -0.0429 | -1.31 | 46% | -0.0712 |
| dist_sma200 | base | -0.0430 | -1.28 | 42% | -0.0358 |
| ret_126 | base | -0.0433 | -1.28 | 40% | -0.0117 |
| tilt_brent | macro | -0.0315 | -0.98 | 40% | -0.0295 |
| rank_sector_mom | sector | -0.0338 | -0.98 | 56% | -0.1166 |
| sector_mom_63 | sector | -0.0338 | -0.98 | 56% | -0.1166 |
| ret_5 | base | -0.0237 | -0.95 | 46% | -0.0145 |
| n_tone_x_attn | news | -0.0212 | -0.90 | 36% | 0.0278 |
| tilt_spx | macro | 0.0253 | 0.86 | 62% | 0.0185 |
| tilt_usdinr | macro | 0.0173 | 0.83 | 54% | -0.0619 |
| tilt_gold | macro | -0.0216 | -0.81 | 48% | 0.0725 |
| n_tone | news | -0.0171 | -0.71 | 42% | -0.0681 |
| tilt_us10y | macro | 0.0175 | 0.65 | 54% | -0.0263 |
| ret_10 | base | -0.0166 | -0.61 | 50% | -0.0401 |
| rank_n_tone_shock | news | -0.0145 | -0.61 | 42% | -0.0429 |
| n_tone_shock | news | -0.0145 | -0.61 | 42% | -0.0429 |
| n_tone_21 | news | -0.0151 | -0.58 | 42% | -0.0712 |
| rank_vol_21 | base | 0.0117 | 0.40 | 54% | 0.0389 |
| vol_21 | base | 0.0117 | 0.40 | 54% | 0.0389 |
| vol_63 | base | 0.0099 | 0.34 | 52% | 0.0706 |
| mom_12_1 | base | 0.0093 | 0.31 | 48% | 0.0048 |
| rank_mom_12_1 | base | 0.0093 | 0.31 | 48% | 0.0048 |

## News event study (sudden very negative / positive company news with an attention spike)

| Period | Bad-news events | Their next-month excess return | t | Good-news events | Excess | t |
|---|---|---|---|---|---|---|
| Training (tone shock + attention spike) | 227 | 0.02% | 0.03 | 109 | 0.83% | 1.52 |
| Holdout (tone shock + attention spike) | 38 | -1.94% | -2.18 | 27 | 0.48% | 0.41 |
| Training (tone shock alone, monthly) | 81 | 0.59% | 0.7 | 78 | -0.54% | -0.78 |
| Holdout (tone shock alone, monthly) | 21 | -0.51% | -0.5 | 10 | 0.79% | 0.39 |

## World/India news mood vs NIFTY's next month

| News topic (21-day tone z-score) | Correlation | t | Months |
|---|---|---|---|
| w_india_econ_z | -0.027 | -0.21 | 64 |
| w_rbi_z | 0.058 | 0.46 | 64 |
| w_india_mkt_z | 0.05 | 0.39 | 64 |
| w_fed_z | -0.014 | -0.11 | 64 |
| w_oil_z | 0.005 | 0.04 | 64 |
| w_tariff_z | 0.121 | 0.96 | 64 |
| w_conflict_z | -0.116 | -0.92 | 64 |
| w_mood | 0.015 | 0.12 | 64 |

Used as model factors only if the walk-forward tests above favour them; not used for market timing (too few independent months to trust a timing rule).

## Caveats
- The stock list is today's NIFTY 50 (survivorship bias) — real results will likely be lower.
- Several setups were compared; the holdout year is the honest check, and it is only one year.
- GDELT tone is a broad lexicon-based measure of news mood, not a reading of each article.
