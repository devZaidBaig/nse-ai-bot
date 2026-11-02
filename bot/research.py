"""Compare strategy variants on the same real data, so changes are chosen on evidence.

    python -m bot.research --years 3
Writes state/research.json and state/research.md, and sends the table as a message.
"""
import argparse
import json

import pandas as pd

from . import config, data, features, notify
from .engine import step
from .metrics import summarize
from .portfolio import Portfolio

VARIANTS = [
    ("A. Weekly AI, 5-day target (original)", dict(REBALANCE_DAYS=7, HORIZON_DAYS=5, STOP_LOSS=0.08)),
    ("B. Monthly AI, 1-month target", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STOP_LOSS=0.08)),
    ("C. Monthly AI, 1-month, wider hold buffer", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, HOLD_BUFFER=20, STOP_LOSS=0.08)),
    ("D. Monthly AI, 1-month, no trailing stop", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STOP_LOSS=None)),
    ("E. Monthly plain momentum (no AI)", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, MODEL="momentum", STOP_LOSS=0.08)),
    ("F. Same as B but ₹1,00,000 account", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STARTING_CAPITAL=100_000, STOP_LOSS=0.08)),
]


def backtest(close, volume, bench, panel, years):
    start = close.index[-1] - pd.DateOffset(years=years)
    days = close.index[close.index >= start]
    pf, ctx = Portfolio(cash=config.STARTING_CAPITAL), {}
    for d in days:
        step(pf, panel, close, bench, d, ctx, retrain_every_days=28)
    eq = pd.Series({pd.Timestamp(e["date"]): e["equity"] for e in pf.equity})
    bn = pd.Series({pd.Timestamp(e["date"]): e["benchmark"] for e in pf.equity})
    s = summarize(eq, bn, pf.trades)
    s["fees_pct_of_capital"] = round(100 * s["total_fees"] / config.STARTING_CAPITAL, 1)
    return s, pf.equity


ROBUSTNESS = [
    (f"{n} [{y}y]", {**o, "_years": y}) for y in (1, 2, 4) for n, o in [
        ("D. Monthly AI, risk-off filter working (40%)", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STOP_LOSS=None)),
        ("H. Monthly AI, no risk-off filter (always 100%)", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STOP_LOSS=None, RISK_OFF_EXPOSURE=1.0)),
        ("I. Monthly AI, risk-off 70%", dict(REBALANCE_DAYS=28, HORIZON_DAYS=21, STOP_LOSS=None, RISK_OFF_EXPOSURE=0.7)),
    ]
]


def main(argv=None):
    global VARIANTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=3.0)
    ap.add_argument("--set", default="robustness", choices=["main", "robustness"])
    a = ap.parse_args(argv)
    if a.set == "robustness":
        VARIANTS = ROBUSTNESS
    close, volume, bench = data.load_prices()
    panels, results = {}, []
    for name, over in VARIANTS:
        years = over.get("_years", a.years)
        over = {k: v for k, v in over.items() if not k.startswith("_")}
        saved = {k: getattr(config, k) for k in over}
        for k, v in over.items():
            setattr(config, k, v)
        try:
            h = config.HORIZON_DAYS
            if h not in panels:
                panels[h] = features.build(close, volume, bench)
            s, eq = backtest(close, volume, bench, panels[h], years)
            results.append({"name": name, "settings": over, "stats": s,
                            "equity": [{"date": e["date"], "equity": e["equity"], "benchmark": e["benchmark"]} for e in eq[::5]]})
            print(f"{name}: {s['total_return_pct']:+.1f}% (NIFTY {s['nifty_return_pct']:+.1f}%), "
                  f"DD {s['max_drawdown_pct']}%, trades {s['trades']}, fees {s['fees_pct_of_capital']}% of capital")
        finally:
            for k, v in saved.items():
                setattr(config, k, v)

    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    (config.STATE_DIR / "research.json").write_text(json.dumps(results, indent=1))
    rows = ["| Variant | Return | NIFTY | CAGR | Sharpe | Max DD | Trades | Win % | Fees (% of capital) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        s = r["stats"]
        rows.append(f"| {r['name']} | {s['total_return_pct']:+.1f}% | {s['nifty_return_pct']:+.1f}% | {s['cagr_pct']}% | "
                    f"{s['sharpe']} | {s['max_drawdown_pct']}% | {s['trades']} | {s['win_rate_pct']} | {s['fees_pct_of_capital']}% |")
    md = f"# Strategy experiments (each row ends {results[0]['stats']['end']})\n\n" + "\n".join(rows) + "\n"
    (config.STATE_DIR / "research.md").write_text(md)
    print(md)
    notify.send("🔬 Strategy experiments finished:\n" + "\n".join(
        f"{r['name']}: {r['stats']['total_return_pct']:+.1f}% vs NIFTY {r['stats']['nifty_return_pct']:+.1f}%" for r in results))


if __name__ == "__main__":
    main()
