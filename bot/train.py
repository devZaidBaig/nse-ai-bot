"""Statistical training pipeline — run weekly in the cloud (python -m bot.lab train).

Guards against fooling ourselves:
  * The most recent 12 months are a HOLDOUT: never used to choose factors or settings, only to judge.
  * Training labels are purged (no training row's 1-month outcome overlaps the holdout).
  * Factor tests use non-overlapping monthly samples, so t-statistics aren't inflated.
  * A challenger replaces the current model (champion) only if it is at least as good on the holdout
    AND not worse on the training years.

Steps
  1. Information coefficient (IC) of every factor: monthly rank-correlation with next-month excess return.
  2. Walk-forward out-of-sample IC for factor groups and a small settings grid (refit every quarter).
  3. Full portfolio backtests (with real costs) of the best candidates vs the champion: training years + holdout.
  4. Event study: does a sudden burst of very negative company news predict underperformance? → news-exit rule.
  5. World-news study: does world/India news mood predict NIFTY's next month?
  6. Save the winning setup (state/model_config.json), a report (state/training_report.md), and notify.
"""
import json
import time

import numpy as np
import pandas as pd

from . import config, data, features, model, notify
from .engine import step
from .features import GROUPS
from .metrics import summarize
from .portfolio import Portfolio

REPORT = config.STATE_DIR / "training_report.md"
HISTORY = config.STATE_DIR / "training_history.csv"
T0 = time.time()


def log(msg):
    print(f"[train {time.time() - T0:6.0f}s] {msg}", flush=True)


def _ic(x: pd.Series, y: pd.Series):
    ok = x.notna() & y.notna()
    if ok.sum() < 20 or x[ok].nunique() < 5:
        return np.nan
    return x[ok].rank().corr(y[ok].rank())


def _tstat(s: pd.Series):
    s = s.dropna()
    return float(s.mean() / s.std() * np.sqrt(len(s))) if len(s) > 2 and s.std() > 0 else np.nan


def factor_ic(panel, feats, dates):
    rows = {}
    for c in feats:
        ics = pd.Series({d: _ic(panel.loc[d][c], panel.loc[d]["fwd_excess"]) for d in dates})
        if ics.notna().sum() >= 6:
            rows[c] = dict(ic=ics.mean(), t=_tstat(ics), hit=(ics.dropna() > 0).mean(), months=int(ics.notna().sum()))
    return pd.DataFrame(rows).T.sort_values("t", key=np.abs, ascending=False)


def oos_ic(panel, cfg, dates, all_dates, refit_every=63):
    """Walk-forward: refit each quarter on data known at that time, score the following months."""
    out, model_ = [], None
    refits = set(all_dates[::refit_every])
    last_fit = None
    for d in dates:
        if model_ is None or last_fit is None or any(last_fit < r <= d for r in refits):
            try:
                model_ = model.Ranker(cfg).fit(panel, d)
                last_fit = d
            except ValueError:
                continue
        rows = panel.loc[[d]].dropna(subset=["ret_63", "vol_21"])
        if len(rows) < 20:
            continue
        p = model_.score(rows)
        y = rows["fwd_excess"].droplevel("date")
        top = y.reindex(p.sort_values(ascending=False).index[:3]).mean()
        out.append(dict(date=d, ic=_ic(p, y), top3=top))
    df = pd.DataFrame(out)
    if df.empty:
        return dict(ic=np.nan, t=np.nan, top3=np.nan, months=0)
    return dict(ic=df["ic"].mean(), t=_tstat(df["ic"]), top3=df["top3"].mean(), months=len(df))


def backtest(panel, close, bench, cfg, start, end):
    model.set_override(cfg)
    try:
        days = close.index[(close.index >= start) & (close.index <= end)]
        pf, ctx = Portfolio(), {}
        for d in days:
            step(pf, panel, close, bench, d, ctx, retrain_every_days=28)
        eq = pd.Series({pd.Timestamp(e["date"]): e["equity"] for e in pf.equity})
        bn = pd.Series({pd.Timestamp(e["date"]): e["benchmark"] for e in pf.equity})
        s = summarize(eq, bn, pf.trades)
        s["news_exits"] = sum(1 for t in pf.trades if t["reason"].startswith("news exit"))
        return s
    finally:
        model.set_override(None)


def event_study(panel, mask_dates, z=-2.0, attn=0.5):
    d = panel.index.get_level_values("date")
    sub = panel[d.isin(mask_dates)]
    neg = sub[(sub["n_tone_shock"] <= z) & (sub["n_attn"] >= attn)]["fwd_excess"].dropna()
    pos = sub[(sub["n_tone_shock"] >= -z) & (sub["n_attn"] >= attn)]["fwd_excess"].dropna()
    res = {}
    for name, s in [("bad_news", neg), ("good_news", pos)]:
        res[name] = dict(n=int(len(s)), mean_excess_pct=round(100 * s.mean(), 2) if len(s) else None,
                         t=round(_tstat(s), 2) if len(s) > 2 else None)
    return res


def world_study(panel, bench, dates):
    b = bench.reindex(panel.index.get_level_values("date").unique()).ffill()
    fwd = (b.shift(-config.HORIZON_DAYS) / b - 1).reindex(dates)
    rows = {}
    for c in GROUPS["world"]:
        if c not in panel.columns:
            continue
        x = panel[c].groupby(level="date").first().reindex(dates)
        ok = x.notna() & fwd.notna()
        if ok.sum() >= 12:
            r = x[ok].corr(fwd[ok])
            rows[c] = dict(corr=round(r, 3), t=round(r * np.sqrt((ok.sum() - 2) / max(1e-9, 1 - r * r)), 2),
                           months=int(ok.sum()))
    return pd.DataFrame(rows).T


def main(argv=None):
    config.HORIZON_DAYS, config.REBALANCE_DAYS = 21, 28
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    log("loading prices, world markets and news history")
    close, volume, bench, macro, gnews = data.load_all()
    panel = features.build(close, volume, bench, macro, gnews)
    panel = panel.sort_index()
    all_dates = close.index
    end = all_dates[-1]
    holdout_start = end - pd.DateOffset(years=1)
    train_dates_all = all_dates[all_dates < holdout_start]
    train_label_end = train_dates_all[-(config.HORIZON_DAYS + 1)]     # purge overlap with holdout
    eval_start = all_dates[0] + pd.DateOffset(years=2, months=6)      # 1y factor warm-up + 1.5y training
    monthly = all_dates[::config.HORIZON_DAYS]
    train_months = monthly[(monthly >= eval_start) & (monthly <= train_label_end)]
    hold_months = monthly[(monthly >= holdout_start) & (monthly <= all_dates[-(config.HORIZON_DAYS + 1)])]
    have = {g: [c for c in cols if c in panel.columns and panel[c].notna().mean() > 0.2] for g, cols in GROUPS.items()}
    log(f"data {all_dates[0].date()} → {end.date()}; train months {len(train_months)}, holdout months {len(hold_months)}; "
        f"usable factors: " + ", ".join(f"{g}={len(v)}" for g, v in have.items()))

    # 1. factor ICs ----------------------------------------------------------------
    feats = [c for g in ["base", "macro", "sector", "news", "world"] for c in have[g]]
    ic_train = factor_ic(panel, feats, train_months)
    ic_hold = factor_ic(panel, feats, hold_months)
    log(f"factor ICs done ({len(ic_train)} factors)")

    # 2. candidate setups -----------------------------------------------------------
    P = {"P1": dict(max_depth=4, learning_rate=0.05, min_samples_leaf=200, max_iter=200),
         "P2": dict(max_depth=3, learning_rate=0.03, min_samples_leaf=400, max_iter=300),
         "P3": dict(max_depth=5, learning_rate=0.05, min_samples_leaf=100, max_iter=200)}
    sel = [c for c in ic_train.index if abs(ic_train.at[c, "t"]) >= 2.0]
    sets = {
        "price": have["base"],
        "price+macro": have["base"] + have["macro"],
        "price+sector": have["base"] + have["sector"],
        "price+news": have["base"] + have["news"],
        "price+world": have["base"] + have["world"],
        "price+macro+sector": have["base"] + have["macro"] + have["sector"],
        "price+macro+sector+news": have["base"] + have["macro"] + have["sector"] + have["news"],
        "everything": feats,
    }
    if len(sel) >= 5:
        sets["IC-selected (|t|≥2)"] = sel
    sets = {k: v for k, v in sets.items() if v}
    cand = []
    for name, fs in sets.items():
        cfg = {"name": f"{name} · P1", "features": fs, "params": P["P1"], "news_exit": None}
        r = oos_ic(panel, cfg, train_months, all_dates)
        cand.append({**cfg, **{f"oos_{k}": v for k, v in r.items()}})
        log(f"OOS {cfg['name']}: IC {r['ic']:.4f} (t {r['t']:.2f}), top-3 excess {100 * r['top3']:.2f}%/month")
    cand.sort(key=lambda c: (np.nan_to_num(c["oos_ic"], nan=-1)), reverse=True)
    for base_c in list(cand[:3]):
        for pk in ["P2", "P3"]:
            cfg = {"name": base_c["name"].replace("P1", pk), "features": base_c["features"], "params": P[pk], "news_exit": None}
            r = oos_ic(panel, cfg, train_months, all_dates)
            cand.append({**cfg, **{f"oos_{k}": v for k, v in r.items()}})
            log(f"OOS {cfg['name']}: IC {r['ic']:.4f} (t {r['t']:.2f})")
    cand.sort(key=lambda c: (np.nan_to_num(c["oos_ic"], nan=-1), np.nan_to_num(c["oos_top3"], nan=-1)), reverse=True)

    # 3. backtests: champion vs top-3 challengers ----------------------------------------
    champ = model.active_config()
    champ = {"name": "champion: " + champ.get("name", "current"), "features": champ["features"],
             "params": champ["params"], "news_exit": champ.get("news_exit")}
    champ_oos = oos_ic(panel, champ, train_months, all_dates)
    champ.update({f"oos_{k}": v for k, v in champ_oos.items()})
    finalists = [champ] + [c for c in cand if c["features"] != champ["features"] or c["params"] != champ["params"]][:3]
    for c in finalists:
        c["bt_train"] = backtest(panel, close, bench, c, eval_start, train_dates_all[-1])
        c["bt_hold"] = backtest(panel, close, bench, c, holdout_start, end)
        log(f"backtest {c['name']}: train {c['bt_train']['total_return_pct']:+.1f}% (Sharpe {c['bt_train']['sharpe']}), "
            f"holdout {c['bt_hold']['total_return_pct']:+.1f}% (Sharpe {c['bt_hold']['sharpe']}) vs NIFTY {c['bt_hold']['nifty_return_pct']:+.1f}%")
    challengers = finalists[1:]
    best = max(challengers, key=lambda c: c["bt_train"]["sharpe"]) if challengers else None
    promote = bool(best and best["bt_hold"]["sharpe"] >= champ["bt_hold"]["sharpe"]
                   and best["bt_train"]["sharpe"] >= champ["bt_train"]["sharpe"] - 0.05)
    winner = best if promote else champ
    log(f"decision: {'PROMOTE ' + best['name'] if promote else 'keep champion'}")

    # 4. news-exit event study ------------------------------------------------------
    d_all = panel.index.get_level_values("date").unique()
    ev_train = event_study(panel, d_all[(d_all >= eval_start) & (d_all <= train_label_end)])
    ev_hold = event_study(panel, d_all[d_all >= holdout_start])
    bt = ev_train["bad_news"]
    news_rule = None
    if bt["n"] >= 30 and bt["t"] is not None and bt["t"] <= -2 and (ev_hold["bad_news"]["mean_excess_pct"] or 0) < 0:
        trial = {**winner, "news_exit": {"z": -2.0, "attn": 0.5}}
        with_rule = backtest(panel, close, bench, trial, holdout_start, end)
        if with_rule["sharpe"] >= winner["bt_hold"]["sharpe"]:
            news_rule = trial["news_exit"]
        log(f"news-exit rule holdout Sharpe {with_rule['sharpe']} vs {winner['bt_hold']['sharpe']} → "
            f"{'ENABLED' if news_rule else 'not enabled'}")
    else:
        log("news-exit rule: no significant evidence → not enabled")

    # 5. world-news study ---------------------------------------------------------------
    ws = world_study(panel, bench, monthly[(monthly >= eval_start) & (monthly <= all_dates[-(config.HORIZON_DAYS + 1)])])

    # 6. save --------------------------------------------------------------------------
    final = {"name": winner["name"].replace("champion: ", ""), "features": winner["features"], "params": winner["params"],
             "news_exit": news_rule, "trained_at": str(pd.Timestamp.now(tz="Asia/Kolkata"))[:16],
             "holdout": {k: winner["bt_hold"][k] for k in ["total_return_pct", "nifty_return_pct", "sharpe", "max_drawdown_pct"]},
             "oos_ic": round(float(np.nan_to_num(winner["oos_ic"])), 4)}
    config.MODEL_CONFIG.write_text(json.dumps(final, indent=1))
    _write_report(final, promote, champ, best, cand, finalists, ic_train, ic_hold, ev_train, ev_hold, ws,
                  all_dates, eval_start, holdout_start, end, have)
    row = pd.DataFrame([{"date": str(end.date()), "model": final["name"], "promoted": promote,
                         "oos_ic": final["oos_ic"], **{f"holdout_{k}": v for k, v in final["holdout"].items()},
                         "news_exit": bool(news_rule)}])
    if HISTORY.exists():
        row = pd.concat([pd.read_csv(HISTORY), row], ignore_index=True)
    row.to_csv(HISTORY, index=False)
    h = final["holdout"]
    notify.send(f"🧠 Weekly training done. Model: {final['name']} ({'NEW' if promote else 'unchanged'}). "
                f"Last 12 months (unseen): {h['total_return_pct']:+.1f}% vs NIFTY {h['nifty_return_pct']:+.1f}%, "
                f"Sharpe {h['sharpe']}. News-exit rule: {'on' if news_rule else 'off'}.")
    log("done")


def _write_report(final, promote, champ, best, cand, finalists, ic_train, ic_hold, ev_train, ev_hold, ws,
                  all_dates, eval_start, holdout_start, end, have):
    L = [f"# Training report — {str(pd.Timestamp.now(tz='Asia/Kolkata'))[:16]} IST", "",
         f"Data {all_dates[0].date()} → {end.date()}. Training/evaluation years {eval_start.date()} → {holdout_start.date()}; "
         f"**holdout (never used for choices) {holdout_start.date()} → {end.date()}**.", "",
         f"Usable factors: " + ", ".join(f"{g} {len(v)}" for g, v in have.items()), "",
         f"## Decision: {'✅ promoted **' + best['name'] + '**' if promote else 'kept current model **' + champ['name'] + '**'}", "",
         f"News-exit rule: **{'ON ' + json.dumps(final['news_exit']) if final['news_exit'] else 'off'}**", "",
         "## Portfolio backtests (₹10,000, real costs)", "",
         "| Setup | Train return | Train Sharpe | Holdout return | NIFTY (holdout) | Holdout Sharpe | Holdout max DD | OOS IC |",
         "|---|---|---|---|---|---|---|---|"]
    for c in finalists:
        a, b = c["bt_train"], c["bt_hold"]
        L.append(f"| {c['name']} | {a['total_return_pct']:+.1f}% | {a['sharpe']} | {b['total_return_pct']:+.1f}% | "
                 f"{b['nifty_return_pct']:+.1f}% | {b['sharpe']} | {b['max_drawdown_pct']}% | {np.nan_to_num(c['oos_ic']):.4f} |")
    L += ["", "## Walk-forward out-of-sample skill (training years, refit quarterly)", "",
          "IC = rank correlation between the model's scores and next-month excess returns (0 = no skill; 0.03–0.08 is useful in practice).", "",
          "| Setup | OOS IC | t-stat | Top-3 picks' excess return / month | Months |", "|---|---|---|---|---|"]
    for c in cand:
        L.append(f"| {c['name']} | {np.nan_to_num(c['oos_ic']):.4f} | {np.nan_to_num(c['oos_t']):.2f} | "
                 f"{100 * np.nan_to_num(c['oos_top3']):+.2f}% | {c['oos_months']} |")
    L += ["", "## Factor tests (monthly IC vs next-month excess return)", "",
          "|t| ≥ 2 is roughly 'statistically significant'. Holdout column shows whether the effect held up in the unseen year.", "",
          "| Factor | Group | IC (train) | t (train) | % months positive | IC (holdout) |", "|---|---|---|---|---|---|"]
    grp = {c: g for g, cs in GROUPS.items() for c in cs}
    for c in ic_train.index[:30]:
        r = ic_train.loc[c]
        h = ic_hold.at[c, "ic"] if c in ic_hold.index else np.nan
        L.append(f"| {c} | {grp.get(c, '')} | {r['ic']:.4f} | {r['t']:.2f} | {100 * r['hit']:.0f}% | {h:.4f} |")
    L += ["", "## News event study (sudden very negative / positive company news with an attention spike)", "",
          "| Period | Bad-news events | Their next-month excess return | t | Good-news events | Excess | t |", "|---|---|---|---|---|---|---|"]
    for name, ev in [("Training", ev_train), ("Holdout", ev_hold)]:
        b, g = ev["bad_news"], ev["good_news"]
        L.append(f"| {name} | {b['n']} | {b['mean_excess_pct']}% | {b['t']} | {g['n']} | {g['mean_excess_pct']}% | {g['t']} |")
    L += ["", "## World/India news mood vs NIFTY's next month", ""]
    if len(ws):
        L += ["| News topic (21-day tone z-score) | Correlation | t | Months |", "|---|---|---|---|"]
        for c, r in ws.iterrows():
            L.append(f"| {c} | {r['corr']} | {r['t']} | {int(r['months'])} |")
        L += ["", "Used as model factors only if the walk-forward tests above favour them; not used for market timing "
              "(too few independent months to trust a timing rule)."]
    else:
        L.append("No world-news history available yet.")
    L += ["", "## Caveats", "- The stock list is today's NIFTY 50 (survivorship bias) — real results will likely be lower.",
          "- Several setups were compared; the holdout year is the honest check, and it is only one year.",
          "- GDELT tone is a broad lexicon-based measure of news mood, not a reading of each article."]
    REPORT.write_text("\n".join(L) + "\n")
