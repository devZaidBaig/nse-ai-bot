"""One trading day of logic, shared by the backtest and the live paper-trader."""
import pandas as pd

from . import config
from .model import Ranker, apply_news, target_weights


def is_rebalance_day(pf, date: pd.Timestamp) -> bool:
    if pf.last_rebalance is None:
        return True
    days = (date - pd.Timestamp(pf.last_rebalance)).days
    n = config.REBALANCE_DAYS
    return days >= n + 3 or (date.weekday() == config.REBALANCE_WEEKDAY and days >= max(n - 3, 3))


def risk_on(bench: pd.Series, date) -> bool:
    b = bench[:date]
    return len(b) < config.REGIME_SMA or b.iloc[-1] > b.iloc[-config.REGIME_SMA:].mean()


def step(pf, panel, close, bench, date, ctx: dict, retrain_every_days=0, news=None):
    """Run stops, maybe retrain + rebalance, then mark-to-market. Returns a dict describing what happened."""
    prices = close.loc[date]
    n_before = len(pf.trades)
    stops = pf.check_stops(prices, date)
    info = {"date": str(date.date()), "rebalanced": False, "stops": stops}

    if is_rebalance_day(pf, date):
        rows = panel.xs(date, level="date", drop_level=False).dropna(subset=["ret_63", "vol_21"])
        if config.MODEL == "momentum":
            raw = pd.Series(rows["rank_mom_12_1"].to_numpy(), index=rows.index.get_level_values("ticker")).fillna(0)
            ctx["model"] = type("M", (), {"trained_on": "plain momentum"})()
        else:
            last_fit = ctx.get("fit_date")
            if ctx.get("model") is None or last_fit is None or (date - last_fit).days >= retrain_every_days:
                ctx["model"] = Ranker().fit(panel, date)
                ctx["fit_date"] = date
            raw = ctx["model"].score(rows)
        scores, veto = apply_news(raw, news)
        on = risk_on(bench, date)
        targets = target_weights(scores, on, held=set(pf.positions), prices=prices,
                                 equity=pf.value(prices), veto=veto)
        pf.rebalance(targets, prices, date)
        info.update(rebalanced=True, risk_on=on, scores=scores.sort_values(ascending=False), veto=veto,
                    targets=targets, trained_on=ctx["model"].trained_on)

    bench_px = bench[:date].iloc[-1]
    pf.mark(prices, date, bench_px)
    info["new_trades"] = pf.trades[n_before:]
    return info
