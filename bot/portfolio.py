"""Simulated broker account: cash, whole-share positions, Indian trading costs, trade log."""
import json
import math
from pathlib import Path

import pandas as pd

from . import config


def cost(value: float, side: str) -> float:
    """Approximate Indian delivery-trade charges in ₹ for one order."""
    c = config.BROKERAGE + config.STT + config.EXCHANGE_AND_GST + config.SLIPPAGE
    fee = value * c + config.FLAT_FEE_PER_ORDER
    if side == "BUY":
        fee += value * config.STAMP_DUTY_BUY
    else:
        fee += config.DP_CHARGE_PER_SELL
    return fee


class Portfolio:
    def __init__(self, cash=config.STARTING_CAPITAL):
        self.cash = float(cash)
        self.positions = {}     # ticker -> {"shares", "entry_price", "entry_date"}
        self.trades = []        # list of dicts
        self.equity = []        # list of {"date", "equity", "cash", "benchmark"}
        self.last_run = None
        self.last_rebalance = None

    # ---------- valuation ----------
    def value(self, prices: pd.Series) -> float:
        return self.cash + sum(p["shares"] * prices.get(t, p["entry_price"])
                               for t, p in self.positions.items())

    # ---------- orders ----------
    def _sell(self, t, shares, price, date, reason):
        p = self.positions[t]
        shares = min(shares, p["shares"])
        if shares <= 0:
            return
        gross = shares * price
        fee = cost(gross, "SELL")
        self.cash += gross - fee
        pnl = (price - p["entry_price"]) * shares - fee
        self.trades.append(dict(date=str(date.date()), ticker=t, side="SELL", shares=int(shares),
                                price=round(price, 2), fees=round(fee, 2), pnl=round(pnl, 2), reason=reason))
        p["shares"] -= shares
        if p["shares"] == 0:
            del self.positions[t]

    def _buy(self, t, shares, price, date, reason):
        if shares <= 0:
            return
        gross = shares * price
        fee = cost(gross, "BUY")
        if gross + fee > self.cash:
            shares = int((self.cash - config.FLAT_FEE_PER_ORDER) / (price * (1 + 0.002)))
            if shares <= 0:
                return
            gross, fee = shares * price, cost(shares * price, "BUY")
        self.cash -= gross + fee
        if t in self.positions:  # average up
            p = self.positions[t]
            total = p["shares"] + shares
            p["entry_price"] = (p["entry_price"] * p["shares"] + price * shares) / total
            p["shares"] = total
        else:
            self.positions[t] = dict(shares=int(shares), entry_price=price, entry_date=str(date.date()), peak=price)
        self.trades.append(dict(date=str(date.date()), ticker=t, side="BUY", shares=int(shares),
                                price=round(price, 2), fees=round(fee, 2), pnl=0.0, reason=reason))

    def check_stops(self, prices: pd.Series, date):
        """Trailing stop: sell if price drops STOP_LOSS below the highest price seen since buying."""
        hit = []
        if not config.STOP_LOSS:
            return hit
        for t in list(self.positions):
            px = prices.get(t)
            if px is None or math.isnan(px):
                continue
            p = self.positions[t]
            p["peak"] = max(p.get("peak", p["entry_price"]), float(px))
            if px <= p["peak"] * (1 - config.STOP_LOSS):
                self._sell(t, p["shares"], float(px), date, "trailing stop")
                hit.append(t)
        return hit

    def rebalance(self, targets: pd.Series, prices: pd.Series, date):
        total = self.value(prices)
        # Sells first (frees cash), then buys
        for t in list(self.positions):
            px = prices.get(t)
            if px is None or math.isnan(px):
                continue
            want = int(total * targets.get(t, 0.0) / px)
            have = self.positions[t]["shares"]
            if t in targets.index:
                continue                     # still a pick: hold it (trimming costs a DP fee each time)
            if want < have and (have - want) * px > 0.10 * total or want == 0:   # trims only if big (each sell costs a DP fee)
                self._sell(t, have - want, px, date, "rebalance" if want else "dropped by model")
        for t, w in targets.sort_values(ascending=False).items():
            px = prices.get(t)
            if px is None or math.isnan(px):
                continue
            have = self.positions.get(t, {}).get("shares", 0)
            want = int(total * w / px)
            if want > have and (want - have) * px > 0.05 * total:   # skip tiny top-ups
                self._buy(t, want - have, px, date, "model pick")
        # Whole shares leave leftover cash: plan extra shares for the cheapest picks, then one order per stock
        cap = total * config.MAX_POSITION_WEIGHT * 1.15
        extra, cash = {}, self.cash - len(targets) * config.FLAT_FEE_PER_ORDER
        while True:
            options = [(prices[t], t) for t in targets.index
                       if t in self.positions and not math.isnan(prices.get(t, float("nan")))
                       and (self.positions[t]["shares"] + extra.get(t, 0) + 1) * prices[t] <= cap
                       and cash >= prices[t] * 1.003]
            if not options:
                break
            px, t = min(options)
            extra[t] = extra.get(t, 0) + 1
            cash -= px * 1.003
        for t, n in extra.items():
            self._buy(t, n, float(prices[t]), date, "use spare cash")
        self.last_rebalance = str(date.date())

    def mark(self, prices: pd.Series, date, bench_px: float):
        self.equity.append(dict(date=str(date.date()), equity=round(self.value(prices), 2),
                                cash=round(self.cash, 2), benchmark=round(float(bench_px), 2)))
        self.last_run = str(date.date())

    # ---------- persistence ----------
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(cash=self.cash, positions=self.positions, trades=self.trades,
                                        equity=self.equity, last_run=self.last_run,
                                        last_rebalance=self.last_rebalance), indent=1))

    @classmethod
    def load(cls, path: Path):
        pf = cls()
        if path.exists():
            d = json.loads(path.read_text())
            pf.cash, pf.positions, pf.trades = d["cash"], d["positions"], d["trades"]
            pf.equity, pf.last_run, pf.last_rebalance = d["equity"], d.get("last_run"), d.get("last_rebalance")
        return pf
