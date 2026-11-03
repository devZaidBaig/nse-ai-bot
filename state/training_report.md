# Training report — 2026-11-03 20:00 IST

Data 2018-11-05 → 2026-11-03. Training/evaluation years 2021-05-05 → 2025-11-03; **holdout (never used for choices) 2025-11-03 → 2026-11-03**.

Usable factors: base 19, macro 15, sector 4, news 6, world 8, finbert 0

## Decision: kept current model **champion: default (price factors only)**

News-exit rule: **off**

## Portfolio backtests (₹10,000, real costs)

| Setup | Train return | Train Sharpe | Holdout return | NIFTY (holdout) | Holdout Sharpe | Holdout max DD | OOS IC |
|---|---|---|---|---|---|---|---|
| champion: default (price factors only) | +57.8% | 0.56 | +19.2% | -7.6% | 0.98 | -16.76% | 0.0376 |
| everything · P2 | +68.6% | 0.66 | -2.1% | -7.6% | -0.04 | -19.69% | 0.0538 |
| price+macro+sector+news · P1 | +131.7% | 0.96 | -14.8% | -7.6% | -0.98 | -19.76% | 0.0491 |
| price+macro+sector+news · P2 | +174.0% | 1.16 | -12.0% | -7.6% | -0.58 | -23.4% | 0.0477 |

## Walk-forward out-of-sample skill (training years, refit quarterly)

IC = rank correlation between the model's scores and next-month excess returns (0 = no skill; 0.03–0.08 is useful in practice).

| Setup | OOS IC | t-stat | Top-3 picks' excess return / month | Months |
|---|---|---|---|---|
| everything · P2 | 0.0538 | 2.03 | +1.40% | 52 |
| price+macro+sector+news · P1 | 0.0491 | 1.90 | +1.21% | 52 |
| price+macro+sector+news · P2 | 0.0477 | 1.84 | +1.62% | 52 |
| price+macro+sector+news · P3 | 0.0465 | 1.79 | +0.42% | 52 |
| everything · P1 | 0.0456 | 1.62 | +1.36% | 52 |
| price+news · P1 | 0.0427 | 1.66 | +1.45% | 52 |
| price+news · P3 | 0.0425 | 1.69 | +1.09% | 52 |
| price+world · P1 | 0.0413 | 1.69 | +1.18% | 52 |
| everything · P3 | 0.0412 | 1.42 | +1.49% | 52 |
| price+macro+sector · P1 | 0.0398 | 1.61 | +0.80% | 52 |
| price · P1 | 0.0376 | 1.62 | +1.75% | 52 |
| price+macro · P1 | 0.0367 | 1.72 | +1.27% | 52 |
| price+news · P2 | 0.0332 | 1.30 | +1.70% | 52 |
| price+sector · P1 | 0.0325 | 1.36 | +0.88% | 52 |

## Factor tests (monthly IC vs next-month excess return)

|t| ≥ 2 is roughly 'statistically significant'. Holdout column shows whether the effect held up in the unseen year.

| Factor | Group | IC (train) | t (train) | % months positive | IC (holdout) |
|---|---|---|---|---|---|
| tilt_usdinr | macro | 0.0542 | 2.44 | 60% | -0.0028 |
| tilt_us10y | macro | -0.0556 | -2.20 | 42% | 0.0574 |
| dist_sma50 | base | -0.0612 | -2.01 | 37% | -0.0464 |
| rel_sector_21 | sector | -0.0435 | -1.84 | 42% | -0.0330 |
| rank_ret_63 | base | -0.0554 | -1.74 | 46% | -0.0443 |
| ret_63 | base | -0.0554 | -1.74 | 46% | -0.0443 |
| rel_sector_63 | sector | -0.0433 | -1.60 | 44% | 0.0141 |
| tilt_spx | macro | 0.0462 | 1.59 | 50% | -0.0273 |
| rsi_14 | base | -0.0460 | -1.55 | 40% | -0.0263 |
| ret_5 | base | -0.0424 | -1.45 | 46% | 0.0029 |
| drawdown_252 | base | -0.0470 | -1.35 | 44% | -0.0408 |
| rank_sector_mom | sector | -0.0381 | -1.25 | 40% | -0.0897 |
| sector_mom_63 | sector | -0.0381 | -1.25 | 40% | -0.0897 |
| rank_ret_21 | base | -0.0320 | -1.06 | 44% | -0.0689 |
| ret_21 | base | -0.0320 | -1.06 | 44% | -0.0689 |
| dist_sma200 | base | -0.0357 | -1.04 | 46% | -0.0476 |
| vol_63 | base | 0.0303 | 0.99 | 56% | 0.0553 |
| tilt_brent | macro | -0.0289 | -0.92 | 46% | -0.0222 |
| ret_10 | base | -0.0251 | -0.89 | 50% | -0.0211 |
| ret_126 | base | -0.0286 | -0.85 | 50% | -0.0824 |
| rank_mom_12_1 | base | 0.0262 | 0.81 | 54% | -0.0217 |
| mom_12_1 | base | 0.0262 | 0.81 | 54% | -0.0217 |
| n_tone_21 | news | -0.0151 | -0.74 | 48% | -0.0230 |
| rank_vol_21 | base | 0.0221 | 0.74 | 52% | 0.0420 |
| vol_21 | base | 0.0221 | 0.74 | 52% | 0.0420 |
| tilt_gold | macro | -0.0180 | -0.63 | 52% | -0.0074 |
| n_tone_x_attn | news | -0.0174 | -0.52 | 46% | nan |
| tilt_indiavix | macro | 0.0126 | 0.47 | 48% | -0.0318 |
| rank_n_tone_shock | news | 0.0133 | 0.46 | 55% | 0.0567 |
| n_tone_shock | news | 0.0133 | 0.46 | 55% | 0.0567 |

## News event study (sudden very negative / positive company news with an attention spike)

| Period | Bad-news events | Their next-month excess return | t | Good-news events | Excess | t |
|---|---|---|---|---|---|---|
| Training | 0 | None% | None | 0 | None% | None |
| Holdout | 0 | None% | None | 0 | None% | None |

## World/India news mood vs NIFTY's next month

| News topic (21-day tone z-score) | Correlation | t | Months |
|---|---|---|---|
| w_india_econ_z | -0.141 | -1.12 | 64 |
| w_rbi_z | -0.086 | -0.68 | 64 |
| w_india_mkt_z | -0.158 | -1.26 | 64 |
| w_fed_z | -0.165 | -1.32 | 64 |
| w_oil_z | -0.134 | -1.06 | 64 |
| w_tariff_z | 0.088 | 0.69 | 64 |
| w_conflict_z | -0.194 | -1.56 | 64 |
| w_mood | -0.162 | -1.3 | 64 |

Used as model factors only if the walk-forward tests above favour them; not used for market timing (too few independent months to trust a timing rule).

## Caveats
- The stock list is today's NIFTY 50 (survivorship bias) — real results will likely be lower.
- Several setups were compared; the holdout year is the honest check, and it is only one year.
- GDELT tone is a broad lexicon-based measure of news mood, not a reading of each article.
