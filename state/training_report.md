# Training report — 2026-11-15 10:52 IST

Data 2018-11-13 → 2026-11-13. Training/evaluation years 2021-05-13 → 2025-11-13; **holdout (never used for choices) 2025-11-13 → 2026-11-13**.

Usable factors: base 19, macro 15, sector 4, news 6, world 8, finbert 0

## Decision: kept current model **champion: price+world · P2**

News-exit rule: **off**

## Portfolio backtests (₹10,000, real costs)

| Setup | Train return | Train Sharpe | Holdout return | NIFTY (holdout) | Holdout Sharpe | Holdout max DD | OOS IC |
|---|---|---|---|---|---|---|---|
| champion: price+world · P2 | +198.5% | 1.2 | +3.4% | -2.8% | 0.29 | -14.23% | 0.0467 |
| price+macro · P1 | +61.1% | 0.58 | -12.8% | -2.8% | -0.95 | -20.68% | 0.0598 |
| price+macro+sector · P1 | +129.1% | 0.95 | -14.8% | -2.8% | -1.07 | -20.84% | 0.0588 |
| price+macro+sector · P2 | +183.6% | 1.22 | -10.1% | -2.8% | -0.6 | -19.61% | 0.0579 |

## Walk-forward out-of-sample skill (training years, refit quarterly)

IC = rank correlation between the model's scores and next-month excess returns (0 = no skill; 0.03–0.08 is useful in practice).

| Setup | OOS IC | t-stat | Top-3 picks' excess return / month | Months |
|---|---|---|---|---|
| price+macro · P1 | 0.0598 | 2.53 | +0.87% | 52 |
| price+macro+sector · P1 | 0.0588 | 2.28 | +0.95% | 52 |
| price+macro+sector · P2 | 0.0579 | 2.31 | +1.01% | 52 |
| price+macro · P2 | 0.0574 | 2.54 | +0.68% | 52 |
| price+macro+sector+news · P2 | 0.0531 | 2.10 | +0.72% | 52 |
| price+macro+sector+news · P1 | 0.0529 | 2.04 | +0.66% | 52 |
| price+macro · P3 | 0.0472 | 2.06 | +0.60% | 52 |
| price+macro+sector+news · P3 | 0.0443 | 1.67 | +0.51% | 52 |
| everything · P1 | 0.0410 | 1.65 | +0.60% | 52 |
| price+macro+sector · P3 | 0.0404 | 1.61 | +0.94% | 52 |
| price+world · P1 | 0.0361 | 1.71 | +1.04% | 52 |
| price+news · P1 | 0.0350 | 1.42 | +1.44% | 52 |
| price+sector · P1 | 0.0275 | 1.19 | +0.69% | 52 |
| price · P1 | 0.0255 | 1.12 | +0.73% | 52 |

## Factor tests (monthly IC vs next-month excess return)

|t| ≥ 2 is roughly 'statistically significant'. Holdout column shows whether the effect held up in the unseen year.

| Factor | Group | IC (train) | t (train) | % months positive | IC (holdout) |
|---|---|---|---|---|---|
| drawdown_252 | base | -0.0575 | -2.18 | 38% | -0.0055 |
| rel_sector_63 | sector | -0.0409 | -1.92 | 42% | 0.0435 |
| dist_sma50 | base | -0.0464 | -1.76 | 42% | 0.0163 |
| rel_sector_21 | sector | -0.0332 | -1.70 | 46% | 0.0699 |
| rank_ret_63 | base | -0.0477 | -1.66 | 40% | 0.0179 |
| ret_63 | base | -0.0477 | -1.66 | 40% | 0.0179 |
| dist_sma200 | base | -0.0404 | -1.31 | 38% | -0.0007 |
| ret_126 | base | -0.0357 | -1.15 | 42% | -0.0201 |
| tilt_gold | macro | -0.0311 | -1.14 | 46% | 0.0983 |
| tilt_usdinr | macro | 0.0215 | 1.00 | 60% | -0.0124 |
| tilt_brent | macro | -0.0303 | -0.99 | 42% | -0.0138 |
| rsi_14 | base | -0.0269 | -0.96 | 44% | -0.0078 |
| tilt_us10y | macro | 0.0255 | 0.93 | 58% | 0.0151 |
| ret_21 | base | -0.0233 | -0.87 | 48% | -0.0116 |
| rank_ret_21 | base | -0.0233 | -0.87 | 48% | -0.0116 |
| n_tone | news | -0.0183 | -0.79 | 55% | 0.0004 |
| rank_mom_12_1 | base | 0.0213 | 0.73 | 52% | -0.0379 |
| mom_12_1 | base | 0.0213 | 0.73 | 52% | -0.0379 |
| vol_63 | base | 0.0158 | 0.54 | 54% | 0.0599 |
| rank_sector_mom | sector | -0.0155 | -0.51 | 50% | -0.0078 |
| sector_mom_63 | sector | -0.0155 | -0.51 | 50% | -0.0078 |
| rank_n_tone_shock | news | -0.0110 | -0.44 | 51% | -0.0000 |
| n_tone_shock | news | -0.0110 | -0.44 | 51% | -0.0000 |
| n_tone_21 | news | -0.0086 | -0.36 | 48% | 0.0252 |
| vol_21 | base | 0.0096 | 0.33 | 50% | 0.0437 |
| rank_vol_21 | base | 0.0096 | 0.33 | 50% | 0.0437 |
| tilt_dxy | macro | -0.0089 | -0.32 | 46% | -0.0277 |
| beta_mkt | macro | -0.0094 | -0.26 | 40% | 0.1047 |
| ret_10 | base | -0.0071 | -0.25 | 48% | 0.0109 |
| tilt_indiavix | macro | -0.0064 | -0.24 | 49% | -0.0681 |

## News event study (sudden very negative / positive company news with an attention spike)

| Period | Bad-news events | Their next-month excess return | t | Good-news events | Excess | t |
|---|---|---|---|---|---|---|
| Training (tone shock + attention spike) | 227 | 0.02% | 0.03 | 110 | 0.8% | 1.48 |
| Holdout (tone shock + attention spike) | 38 | -1.94% | -2.18 | 27 | 0.48% | 0.41 |
| Training (tone shock alone, monthly) | 71 | 0.78% | 1.01 | 56 | 0.61% | 0.71 |
| Holdout (tone shock alone, monthly) | 22 | 0.18% | 0.24 | 4 | 1.18% | 1.23 |

## World/India news mood vs NIFTY's next month

| News topic (21-day tone z-score) | Correlation | t | Months |
|---|---|---|---|
| w_india_econ_z | -0.077 | -0.61 | 64 |
| w_rbi_z | -0.086 | -0.68 | 64 |
| w_india_mkt_z | -0.111 | -0.88 | 64 |
| w_fed_z | -0.043 | -0.34 | 64 |
| w_oil_z | 0.02 | 0.16 | 64 |
| w_tariff_z | 0.221 | 1.78 | 64 |
| w_conflict_z | -0.038 | -0.3 | 64 |
| w_mood | -0.024 | -0.19 | 64 |

Used as model factors only if the walk-forward tests above favour them; not used for market timing (too few independent months to trust a timing rule).

## Caveats
- The stock list is today's NIFTY 50 (survivorship bias) — real results will likely be lower.
- Several setups were compared; the holdout year is the honest check, and it is only one year.
- GDELT tone is a broad lexicon-based measure of news mood, not a reading of each article.
