"""Entry point.

    python -m bot.main backtest          # train/test on past data with dummy money
    python -m bot.main decide            # main daily run (~3:05 PM IST, market still open, live prices)
    python -m bot.main watch             # intraday check: trailing stops on live prices
    python -m bot.main report            # rebuild the dashboard
Add --force to decide/watch to run outside market hours or re-run the same day.
"""
import argparse
import json
import sys

import pandas as pd

from . import config, data, features, news, notify, report
from .engine import step
from .metrics import summarize
from .portfolio import Portfolio

STATE = config.STATE_DIR / "portfolio.json"
BACKTEST = config.STATE_DIR / "backtest.json"


def _now_ist():
    return pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)


def _inr(v):
    return f"₹{v:,.0f}"


# ------------------------------------------------------------------ backtest
def run_backtest(years: float):
    close, volume, bench, macro, gnews = data.load_all()
    panel = features.build(close, volume, bench, macro, gnews)
    start = close.index[-1] - pd.DateOffset(years=years)
    days = close.index[close.index >= start]
    pf, ctx = Portfolio(), {}
    print(f"[backtest] {days[0].date()} → {days[-1].date()}  ({len(days)} trading days, {_inr(config.STARTING_CAPITAL)} start)")
    for i, d in enumerate(days):
        step(pf, panel, close, bench, d, ctx, retrain_every_days=28)   # retrain monthly for speed
        if i % 60 == 0:
            print(f"  {d.date()}  equity {_inr(pf.equity[-1]['equity'])}")
    eq = pd.Series({pd.Timestamp(e["date"]): e["equity"] for e in pf.equity})
    bn = pd.Series({pd.Timestamp(e["date"]): e["benchmark"] for e in pf.equity})
    stats = summarize(eq, bn, pf.trades)
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    BACKTEST.write_text(json.dumps({"stats": stats, "equity": pf.equity, "trades": pf.trades[-300:]}, indent=1))
    print(json.dumps(stats, indent=2))
    report.build()
    s = stats
    notify.send(f"🧪 Backtest done ({s['start']} → {s['end']}, {_inr(config.STARTING_CAPITAL)} dummy money)\n"
                f"Bot {s['total_return_pct']:+.1f}% vs NIFTY {s['nifty_return_pct']:+.1f}%\n"
                f"Max drawdown {s['max_drawdown_pct']}% · win rate {s['win_rate_pct']}% · fees {_inr(s['total_fees'])}")


# ------------------------------------------------------------------ main daily decision
def run_decide(force: bool):
    pf = Portfolio.load(STATE)
    close, volume, bench, macro, gnews = data.load_all()
    today = close.index[-1]
    if not force:
        if today.normalize() < _now_ist().normalize():
            print(f"[decide] latest data is {today.date()} — NSE closed today (holiday). Skipping.")
            return
        if pf.last_run == str(today.date()):
            print(f"[decide] already ran for {today.date()}. Skipping.")
            return

    sentiment = None
    if config.NEWS_ENABLED:
        try:
            sentiment = news.today_sentiment(list(close.columns), today)
        except Exception as e:
            print(f"[news] skipped: {e}")
    panel = features.build(close, volume, bench, macro, gnews)
    info = step(pf, panel, close, bench, today, {}, retrain_every_days=0, news=sentiment)
    pf.save(STATE)
    px = close.loc[today].dropna()
    (config.STATE_DIR / "last_prices.json").write_text(json.dumps(
        {"date": str(today.date()), "prices": {t: round(float(v), 2) for t, v in px.items()}}))
    if sentiment is not None:
        (config.STATE_DIR / "news_today.json").write_text(
            sentiment.sort_values("sentiment").reset_index(names="ticker").to_json(orient="records"))

    msg = _daily_message(pf, info, px, sentiment)
    if today.weekday() == config.WEEKLY_RECAP_WEEKDAY:
        msg += "\n\n" + _weekly_recap(pf)
    print(msg)
    (config.STATE_DIR / "latest.txt").write_text(msg + "\n")
    report.build()
    notify.send(msg)


def _daily_message(pf, info, px, sentiment):
    eq0, eq = config.STARTING_CAPITAL, pf.equity[-1]["equity"]
    prev = pf.equity[-2]["equity"] if len(pf.equity) > 1 else eq0
    b = [e["benchmark"] for e in pf.equity]
    nifty = 100 * (b[-1] / b[0] - 1) if len(b) > 1 else 0.0
    L = [f"📈 *NSE AI bot* — {info['date']}",
         f"Value {_inr(eq)}  (today {100 * (eq / prev - 1):+.2f}%, total {100 * (eq / eq0 - 1):+.2f}% vs NIFTY {nifty:+.2f}%)",
         f"Cash {_inr(pf.cash)}"]
    if info["new_trades"]:
        L.append("Trades:")
        for t in info["new_trades"]:
            extra = f", P&L {_inr(t['pnl'])}" if t["side"] == "SELL" else ""
            L.append(f" • {t['side']} {t['shares']} {t['ticker']} @ ₹{t['price']:,.2f} ({t['reason']}{extra})")
    else:
        L.append("No trades today.")
    if pf.positions:
        L.append("Holding:")
        for t, p in pf.positions.items():
            last = float(px.get(t, p["entry_price"]))
            L.append(f" • {t} ×{p['shares']}  {100 * (last / p['entry_price'] - 1):+.1f}%")
    if pf.last_rebalance and not info["rebalanced"]:
        nxt = pd.Timestamp(pf.last_rebalance) + pd.Timedelta(days=max(config.REBALANCE_DAYS - 3, 3))
        nxt += pd.Timedelta(days=(config.REBALANCE_WEEKDAY - nxt.weekday()) % 7)
        L.append(f"Next review of picks: around {nxt:%d %b}")
    if info["rebalanced"]:
        L.append(f"Market mood: {'risk-ON ✅' if info['risk_on'] else 'risk-OFF ⚠️ (investing less)'}")
        if info.get("veto"):
            L.append("Skipped on bad news: " + ", ".join(sorted(info["veto"])))
    if sentiment is not None and len(sentiment):
        held = [t for t in pf.positions if t in sentiment.index and sentiment.loc[t, "count"] > 0]
        for t in held[:3]:
            s = sentiment.loc[t]
            L.append(f"📰 {t} news {s['sentiment']:+.2f}: {str(s['headline'])[:90]}")
    return "\n".join(L)


def _weekly_recap(pf):
    eq = pd.Series({pd.Timestamp(e["date"]): e["equity"] for e in pf.equity})
    wk = eq[eq.index > eq.index[-1] - pd.Timedelta(days=7)]
    base = eq[eq.index <= eq.index[-1] - pd.Timedelta(days=7)]
    start = base.iloc[-1] if len(base) else config.STARTING_CAPITAL
    week_trades = [t for t in pf.trades if pd.Timestamp(t["date"]) > eq.index[-1] - pd.Timedelta(days=7)]
    closed = [t for t in pf.trades if t["side"] == "SELL"]
    wins = sum(t["pnl"] > 0 for t in closed)
    return (f"🗓️ *Weekly recap*: {100 * (wk.iloc[-1] / start - 1):+.2f}% this week, "
            f"{len(week_trades)} trades. All-time: {len(closed)} closed trades, "
            f"{(100 * wins / len(closed)) if closed else 0:.0f}% winners, fees {_inr(sum(t['fees'] for t in pf.trades))}.")


# ------------------------------------------------------------------ intraday watch
def run_watch(force: bool):
    pf = Portfolio.load(STATE)
    if not pf.positions:
        print("[watch] no open positions.")
        return
    now = _now_ist()
    if not force and (now.weekday() > 4 or not (pd.Timestamp("09:20").time() <= now.time() <= pd.Timestamp("15:30").time())):
        print("[watch] market closed.")
        return
    quotes = data.live_quotes(pf.positions.keys())
    if quotes.empty:
        print("[watch] no live quotes (holiday?).")
        return
    n = len(pf.trades)
    hits = pf.check_stops(quotes, now)
    pf.save(STATE)
    if not config.STOP_LOSS:
        lp = config.STATE_DIR / "last_prices.json"
        prev = json.loads(lp.read_text())["prices"] if lp.exists() else {}
        alerted_file = config.STATE_DIR / "alerts_today.json"
        alerted = json.loads(alerted_file.read_text()) if alerted_file.exists() else {}
        if alerted.get("date") != str(now.date()):
            alerted = {"date": str(now.date()), "tickers": []}
        L = []
        for t, p in pf.positions.items():
            q, pc = quotes.get(t), prev.get(t)
            if q is None or not pc or t in alerted["tickers"]:
                continue
            chg = q / pc - 1
            if chg <= -config.INTRADAY_ALERT:
                L.append(f" • {t} ₹{q:,.2f} ({100 * chg:+.1f}% today, {100 * (q / p['entry_price'] - 1):+.1f}% vs our cost)")
                alerted["tickers"].append(t)
        alerted_file.write_text(json.dumps(alerted))
        if L:
            msg = "\n".join([f"⚠️ *NSE AI bot* — big drop alert ({now:%d %b %H:%M} IST)", *L,
                              "No action taken: the strategy holds through dips and reviews picks at the monthly rebalance."])
            print(msg)
            notify.send(msg)
        else:
            print("[watch] no big moves: " + ", ".join(f"{t} ₹{quotes.get(t, float('nan')):,.2f}" for t in pf.positions))
        return
    if hits:
        L = [f"🚨 *NSE AI bot* — trailing stop hit ({now:%d %b %H:%M} IST)"]
        for t in pf.trades[n:]:
            L.append(f" • SOLD {t['shares']} {t['ticker']} @ ₹{t['price']:,.2f}, P&L {_inr(t['pnl'])}")
        L.append(f"Cash now {_inr(pf.cash)}. Money gets reinvested at the next weekly rebalance.")
        msg = "\n".join(L)
        print(msg)
        report.build()
        notify.send(msg)
    else:
        print("[watch] all positions OK: " + ", ".join(f"{t} ₹{quotes.get(t, float('nan')):,.2f}" for t in pf.positions))


# ------------------------------------------------------------------ morning: news refresh + check
def run_morning(force: bool):
    """Refresh GDELT news history (yesterday's news), check holdings for news shocks, then live-price watch."""
    from . import gdelt
    try:
        gdelt.update(max_minutes=40)
    except Exception as e:
        print(f"[morning] news refresh failed: {e}")
    pf = Portfolio.load(STATE)
    L = [f"🌅 *NSE AI bot* — morning news check {_now_ist():%d %b}"]
    try:
        close, volume, bench, macro, gnews = data.load_all()
        panel = features.build(close, volume, bench, macro, gnews)
        last = panel.xs(close.index[-1], level="date")
        for t in pf.positions:
            if t in last.index and pd.notna(last.at[t, "n_tone_shock"]):
                z, a = last.at[t, "n_tone_shock"], last.at[t, "n_attn"]
                flag = " ⚠️" if z <= -2 else (" 👍" if z >= 2 else "")
                L.append(f" • {t}: news tone {z:+.1f}σ vs its normal, attention {a:+.1f}{flag}")
        wm = last["w_mood"].dropna()
        if len(wm):
            L.append(f"World/India news mood: {wm.iloc[0]:+.1f}σ vs the past year")
    except Exception as e:
        L.append(f"(news check unavailable: {e.__class__.__name__})")
    msg = "\n".join(L)
    print(msg)
    (config.STATE_DIR / "morning.txt").write_text(msg + "\n")
    run_watch(force)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["backtest", "decide", "daily", "watch", "morning", "report", "test-message"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--years", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.cmd == "backtest":
        run_backtest(a.years)
    elif a.cmd in ("decide", "daily"):
        run_decide(a.force)
    elif a.cmd == "watch":
        run_watch(a.force)
    elif a.cmd == "morning":
        run_morning(a.force)
    elif a.cmd == "test-message":
        notify.send("✅ NSE AI bot: messages are working! You'll get a daily update on trading days around 3:10 PM IST.")
    else:
        report.build()


if __name__ == "__main__":
    sys.exit(main())
