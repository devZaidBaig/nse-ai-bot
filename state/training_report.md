# Training report — 2026-11-08 10:51 IST

Data 2018-11-06 → 2026-11-06. Training/evaluation years 2021-05-06 → 2025-11-06; **holdout (never used for choices) 2025-11-06 → 2026-11-06**.

Usable factors: base 19, macro 15, sector 4, news 6, world 8, finbert 0

## Decision: ✅ promoted **price+world · P2**

News-exit rule: **off**

## Portfolio backtests (₹10,000, real costs)

| Setup | Train return | Train Sharpe | Holdout return | NIFTY (holdout) | Holdout Sharpe | Holdout max DD | OOS IC |
|---|---|---|---|---|---|---|---|
| champion: default (price factors only) | +123.3% | 0.86 | -12.8% | -1.9% | -0.89 | -16.63% | 0.0435 |
| price+world · P1 | +179.1% | 1.03 | +1.9% | -1.9% | 0.2 | -13.64% | 0.0578 |
| price+world · P2 | +176.3% | 1.06 | -0.7% | -1.9% | 0.03 | -13.58% | 0.0544 |
| price+macro+sector · P2 | +106.6% | 0.85 | -11.5% | -1.9% | -0.64 | -19.98% | 0.0496 |

## Walk-forward out-of-sample skill (training years, refit quarterly)

IC = rank correlation between the model's scores and next-month excess returns (0 = no skill; 0.03–0.08 is useful in practice).

| Setup | OOS IC | t-stat | Top-3 picks' excess return / month | Months |
|---|---|---|---|---|
| price+world · P1 | 0.0578 | 2.40 | +0.83% | 52 |
| price+world · P2 | 0.0544 | 2.23 | +1.45% | 52 |
| price+macro+sector · P2 | 0.0496 | 2.04 | +2.18% | 52 |
| price+news · P2 | 0.0494 | 1.84 | +0.80% | 52 |
| price+news · P3 | 0.0469 | 2.02 | +0.93% | 52 |
| price+macro+sector · P1 | 0.0462 | 2.03 | +1.16% | 52 |
| price+news · P1 | 0.0457 | 1.77 | +1.21% | 52 |
| price+macro · P1 | 0.0453 | 2.10 | +1.21% | 52 |
| everything · P1 | 0.0446 | 1.98 | +0.71% | 52 |
| price · P1 | 0.0435 | 1.84 | +1.46% | 52 |
| price+macro+sector+news · P1 | 0.0414 | 1.74 | +0.74% | 52 |
| price+world · P3 | 0.0412 | 1.61 | +1.60% | 52 |
| IC-selected (|t|≥2) · P1 | 0.0411 | 1.78 | +1.47% | 52 |
| price+macro+sector · P3 | 0.0386 | 1.65 | +1.13% | 52 |
| price+sector · P1 | 0.0288 | 1.21 | +0.88% | 52 |

## Factor tests (monthly IC vs next-month excess return)

|t| ≥ 2 is roughly 'statistically significant'. Holdout column shows whether the effect held up in the unseen year.

| Factor | Group | IC (train) | t (train) | % months positive | IC (holdout) |
|---|---|---|---|---|---|
| rel_sector_21 | sector | -0.0530 | -2.40 | 38% | -0.0330 |
| tilt_gold | macro | -0.0551 | -2.12 | 40% | 0.0125 |
| dist_sma50 | base | -0.0621 | -2.11 | 37% | -0.0456 |
| rank_ret_63 | base | -0.0606 | -2.00 | 44% | -0.0641 |
| ret_63 | base | -0.0606 | -2.00 | 44% | -0.0641 |
| rsi_14 | base | -0.0512 | -1.83 | 46% | -0.0364 |
| rel_sector_63 | sector | -0.0481 | -1.81 | 42% | 0.0032 |
| n_attn | news | -0.0385 | -1.73 | 37% | 0.0171 |
| drawdown_252 | base | -0.0527 | -1.67 | 38% | -0.0337 |
| tilt_us10y | macro | -0.0395 | -1.56 | 37% | -0.0013 |
| ret_5 | base | -0.0424 | -1.55 | 35% | 0.0197 |
| tilt_brent | macro | -0.0465 | -1.48 | 35% | -0.0413 |
| tilt_dxy | macro | -0.0357 | -1.43 | 44% | 0.0368 |
| rank_ret_21 | base | -0.0393 | -1.41 | 42% | -0.0611 |
| ret_21 | base | -0.0393 | -1.41 | 42% | -0.0611 |
| tilt_usdinr | macro | 0.0297 | 1.39 | 54% | -0.0096 |
| ret_10 | base | -0.0389 | -1.36 | 46% | -0.0398 |
| dist_sma200 | base | -0.0447 | -1.32 | 44% | -0.0419 |
| ret_126 | base | -0.0383 | -1.19 | 50% | -0.0777 |
| tilt_spx | macro | 0.0325 | 1.15 | 58% | -0.0337 |
| sector_mom_63 | sector | -0.0335 | -1.12 | 46% | -0.0866 |
| rank_sector_mom | sector | -0.0335 | -1.12 | 46% | -0.0866 |
| rank_n_tone_shock | news | 0.0256 | 1.09 | 55% | 0.0610 |
| n_tone_shock | news | 0.0256 | 1.09 | 55% | 0.0610 |
| vol_63 | base | 0.0287 | 0.94 | 52% | 0.0416 |
| tilt_indiavix | macro | -0.0240 | -0.87 | 46% | -0.0306 |
| rank_mom_12_1 | base | 0.0220 | 0.68 | 50% | -0.0285 |
| mom_12_1 | base | 0.0220 | 0.68 | 50% | -0.0285 |
| volume_ratio | base | -0.0126 | -0.50 | 46% | 0.0763 |
| n_tone_x_attn | news | 0.0117 | 0.49 | 55% | -0.0725 |

## News event study (sudden very negative / positive company news with an attention spike)

| Period | Bad-news events | Their next-month excess return | t | Good-news events | Excess | t |
|---|---|---|---|---|---|---|
| Training (tone shock + attention spike) | 227 | 0.02% | 0.03 | 110 | 0.8% | 1.48 |
| Holdout (tone shock + attention spike) | 38 | -1.94% | -2.18 | 27 | 0.48% | 0.41 |
| Training (tone shock alone, monthly) | 74 | 0.08% | 0.14 | 57 | 0.61% | 0.72 |
| Holdout (tone shock alone, monthly) | 16 | -1.72% | -1.19 | 15 | -2.39% | -1.71 |

## World/India news mood vs NIFTY's next month

| News topic (21-day tone z-score) | Correlation | t | Months |
|---|---|---|---|
| w_india_econ_z | -0.093 | -0.74 | 64 |
| w_rbi_z | -0.113 | -0.89 | 64 |
| w_india_mkt_z | -0.151 | -1.2 | 64 |
| w_fed_z | -0.147 | -1.17 | 64 |
| w_oil_z | -0.106 | -0.84 | 64 |
| w_tariff_z | 0.128 | 1.01 | 64 |
| w_conflict_z | -0.154 | -1.23 | 64 |
| w_mood | -0.132 | -1.04 | 64 |

Used as model factors only if the walk-forward tests above favour them; not used for market timing (too few independent months to trust a timing rule).

## Caveats
- The stock list is today's NIFTY 50 (survivorship bias) — real results will likely be lower.
- Several setups were compared; the holdout year is the honest check, and it is only one year.
- GDELT tone is a broad lexicon-based measure of news mood, not a reading of each article.
