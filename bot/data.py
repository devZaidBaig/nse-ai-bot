"""Market data: real NSE prices from Yahoo Finance, or synthetic prices for offline testing."""
import os
import numpy as np
import pandas as pd

from . import config


def load_prices():
    """Return (close, volume, benchmark) — close/volume are DataFrames [date x ticker]."""
    if os.environ.get("BOT_SYNTHETIC") == "1":
        return _synthetic()
    return _yahoo()


def _yahoo():
    import yfinance as yf

    tickers = [f"{t}.NS" for t in config.UNIVERSE] + [config.BENCHMARK]
    raw = yf.download(
        tickers, period=f"{config.HISTORY_YEARS}y", interval="1d",
        auto_adjust=True, progress=False, group_by="column", threads=True,
    )
    close = raw["Close"].copy()
    volume = raw["Volume"].copy()
    bench = close.pop(config.BENCHMARK).dropna()
    volume = volume.drop(columns=[config.BENCHMARK], errors="ignore")
    close.columns = [c.replace(".NS", "") for c in close.columns]
    volume.columns = [c.replace(".NS", "") for c in volume.columns]

    # Drop tickers that failed or have too little history
    good = [c for c in close.columns if close[c].notna().sum() > 300]
    missing = sorted(set(config.UNIVERSE) - set(good))
    if missing:
        print(f"[data] skipped (no/short data): {', '.join(missing)}")
    close, volume = close[good], volume[good]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    volume.index = close.index
    bench.index = pd.to_datetime(bench.index).tz_localize(None)
    close = close.ffill(limit=3)
    close, volume = _cut_corporate_actions(close, volume)
    return close, volume, bench


def _cut_corporate_actions(close, volume, gap=0.30):
    """A >30% one-day jump in a NIFTY 50 stock is almost always an unadjusted demerger/split,
    not a real move. Drop the history before it so the model doesn't learn from a fake crash."""
    r = close.pct_change(fill_method=None).abs()
    for t in close.columns:
        hits = r.index[r[t] > gap]
        if len(hits):
            cut = hits[-1]
            print(f"[data] {t}: {r.loc[cut, t]:.0%} jump on {cut.date()} (likely corporate action) — using data after it")
            close.loc[:cut - pd.Timedelta(days=1), t] = np.nan
            volume.loc[:cut - pd.Timedelta(days=1), t] = np.nan
    return close, volume


def _synthetic(n_days=1800, seed=None):
    """Random-walk prices with persistent drifts (so there is momentum for the model to find)."""
    seed = int(os.environ.get("BOT_SEED", "7")) if seed is None else seed
    rng = np.random.default_rng(seed)
    today = pd.Timestamp(os.environ.get("BOT_TODAY", pd.Timestamp.today().normalize()))
    dates = pd.bdate_range(end="2027-12-31", periods=n_days)   # fixed path, then cut at "today"
    names = config.UNIVERSE
    market = rng.normal(0.0004, 0.010, n_days)
    drift = np.zeros(len(names))
    rets = np.empty((n_days, len(names)))
    for i in range(n_days):
        drift = 0.995 * drift + rng.normal(0, 0.00012, len(names))   # slowly changing trends
        rets[i] = market[i] + drift + rng.normal(0, 0.015, len(names))
    level = np.random.default_rng(99).uniform(np.log(150), np.log(9000), len(names))   # realistic ₹150–₹9,000 prices
    close = pd.DataFrame(np.exp(level) * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=names)
    volume = pd.DataFrame(rng.lognormal(13, 0.4, (n_days, len(names))), index=dates, columns=names)
    bench = pd.Series(10000 * np.exp(np.cumsum(market)), index=dates)
    return close[:today], volume[:today], bench[:today]


def live_quotes(tickers) -> pd.Series:
    """Latest intraday prices (Yahoo, a few minutes delayed) for the given NSE tickers."""
    tickers = list(tickers)
    if not tickers:
        return pd.Series(dtype=float)
    if os.environ.get("BOT_SYNTHETIC") == "1":
        close, _, _ = _synthetic()
        rng = np.random.default_rng(int(os.environ.get("BOT_INTRADAY_SEED", "1")))
        last = close.iloc[-1][tickers]
        return last * (1 + rng.normal(0, 0.03, len(tickers)))
    import yfinance as yf
    raw = yf.download([f"{t}.NS" for t in tickers], period="1d", interval="5m",
                      progress=False, auto_adjust=True, group_by="column")
    last = raw["Close"].ffill().iloc[-1]
    last.index = [c.replace(".NS", "") for c in last.index]
    return last.dropna()


def load_macro(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily closes of world/macro factors aligned to NSE trading days (previous value carried forward)."""
    if os.environ.get("BOT_SYNTHETIC") == "1":
        rng = np.random.default_rng(11)
        cols = list(config.MACRO)
        walk = np.exp(np.cumsum(rng.normal(0, 0.01, (len(index), len(cols))), axis=0)) * 100
        return pd.DataFrame(walk, index=index, columns=cols)
    import yfinance as yf
    raw = yf.download(list(config.MACRO.values()), period=f"{config.HISTORY_YEARS}y", interval="1d",
                      auto_adjust=True, progress=False, group_by="column", threads=True)["Close"]
    raw.index = pd.to_datetime(raw.index).tz_localize(None).normalize()
    inv = {v: k for k, v in config.MACRO.items()}
    raw = raw.rename(columns=inv)
    # Foreign markets close after India: only use values up to the previous calendar day (no look-ahead)
    raw = raw.shift(1)
    out = raw.reindex(raw.index.union(index)).ffill().reindex(index)
    missing = [c for c in config.MACRO if c not in out.columns or out[c].notna().sum() < 200]
    if missing:
        print(f"[data] macro factors unavailable: {missing}")
    return out[[c for c in config.MACRO if c in out.columns]]


def load_all():
    """Prices, volume, NIFTY, world-market factors and GDELT news history, all aligned to NSE trading days."""
    from . import gdelt
    close, volume, bench = load_prices()
    try:
        macro = load_macro(close.index)
    except Exception as e:
        print(f"[data] macro factors failed: {e}")
        macro = None
    try:
        g = gdelt.load(close.columns, close.index)
    except Exception as e:
        print(f"[data] news history failed: {e}")
        g = {}
    return close, volume, bench, macro, g
