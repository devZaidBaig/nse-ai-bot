"""Turn prices, world-market data and news history into the factors the model learns from.

Factor groups (the training pipeline tests each group statistically before using it):
  base    – price momentum, volatility, trend, volume, rank vs peers, market trend
  macro   – world markets (rupee, crude, US yields, S&P 500, India VIX, gold, dollar) and each stock's
            measured sensitivity to them × their recent move ("how is today's world likely to hit this stock")
  sector  – sector momentum and the stock's strength vs its own sector
  news    – company news tone/attention from GDELT: level, 21-day trend, sudden shocks vs its own history
  world   – world/India news mood (economy, RBI, Fed, oil, recession, tariffs, conflict)
  finbert – live FinBERT headline scores (only usable once months of history exist)
"""
import numpy as np
import pandas as pd

from . import config, news

GROUPS = {
    "base": ["ret_5", "ret_10", "ret_21", "ret_63", "ret_126", "mom_12_1", "vol_21", "vol_63", "rsi_14",
             "dist_sma50", "dist_sma200", "drawdown_252", "volume_ratio", "rank_ret_21", "rank_ret_63",
             "rank_mom_12_1", "rank_vol_21", "mkt_ret_21", "mkt_above_sma200"],
    "macro": ["beta_mkt"] + [f"m_{k}_ret21" for k in config.MACRO] + [f"tilt_{k}" for k in config.MACRO],
    "sector": ["sector_mom_63", "rank_sector_mom", "rel_sector_63", "rel_sector_21"],
    "news": ["n_tone", "n_tone_21", "n_tone_shock", "n_attn", "rank_n_tone_shock", "n_tone_x_attn"],
    "world": [],   # filled below from gdelt.WORLD_QUERIES
    "finbert": ["news_sent", "news_count"],
}
try:
    from .gdelt import WORLD_QUERIES
    GROUPS["world"] = [f"w_{k[2:].lower()}_z" for k in WORLD_QUERIES] + ["w_mood"]
except Exception:   # pragma: no cover
    pass

ALL_FEATURES = [c for g in GROUPS.values() for c in g]
FEATURES = GROUPS["base"]           # default if no trained model config exists yet


def _rsi(close: pd.DataFrame, n=14) -> pd.DataFrame:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / down.replace(0, np.nan))


def _broadcast(s: pd.Series, cols) -> pd.DataFrame:
    return pd.DataFrame(np.repeat(s.to_numpy()[:, None], len(cols), axis=1), index=s.index, columns=cols)


def _rolling_beta(y: pd.DataFrame, x: pd.Series, n=252) -> pd.DataFrame:
    """Rolling OLS beta of each column of y on x (daily returns)."""
    mx = x.rolling(n, min_periods=120).mean()
    vx = x.rolling(n, min_periods=120).var()
    out = {}
    for c in y.columns:
        cov = (y[c] * x).rolling(n, min_periods=120).mean() - y[c].rolling(n, min_periods=120).mean() * mx
        out[c] = cov / vx
    return pd.DataFrame(out)


def _z(df, n=252, minp=60):
    return (df - df.rolling(n, min_periods=minp).mean()) / df.rolling(n, min_periods=minp).std()


def build(close: pd.DataFrame, volume: pd.DataFrame, bench: pd.Series,
          macro: pd.DataFrame | None = None, gdelt: dict | None = None) -> pd.DataFrame:
    """Long panel indexed by (date, ticker) with all available factors, 'fwd_ret' and 'label'."""
    cols, idx = close.columns, close.index
    daily = close.pct_change(fill_method=None)
    f = {
        "ret_5": close.pct_change(5, fill_method=None),
        "ret_10": close.pct_change(10, fill_method=None),
        "ret_21": close.pct_change(21, fill_method=None),
        "ret_63": close.pct_change(63, fill_method=None),
        "ret_126": close.pct_change(126, fill_method=None),
        "mom_12_1": close.shift(21) / close.shift(252) - 1,
        "vol_21": daily.rolling(21).std() * np.sqrt(252),
        "vol_63": daily.rolling(63).std() * np.sqrt(252),
        "rsi_14": _rsi(close),
        "dist_sma50": close / close.rolling(50).mean() - 1,
        "dist_sma200": close / close.rolling(200).mean() - 1,
        "drawdown_252": close / close.rolling(252).max() - 1,
        "volume_ratio": volume.rolling(5).mean() / volume.rolling(63).mean(),
    }
    for k in ["ret_21", "ret_63", "mom_12_1", "vol_21"]:
        f[f"rank_{k}"] = f[k].rank(axis=1, pct=True)

    b = bench.reindex(idx).ffill()
    f["mkt_ret_21"] = _broadcast(b.pct_change(21, fill_method=None), cols)
    f["mkt_above_sma200"] = _broadcast((b > b.rolling(config.REGIME_SMA).mean()).astype(float), cols)

    # ---- macro: world markets and each stock's sensitivity to them ----
    f["beta_mkt"] = _rolling_beta(daily, b.pct_change(fill_method=None))
    if macro is not None and len(macro.columns):
        for k in macro.columns:
            m = macro[k].ffill()
            mret = m.pct_change(fill_method=None) if k != "us10y" else m.diff() / 10   # yield: change in %-points
            m21 = m.pct_change(21, fill_method=None) if k != "us10y" else m.diff(21) / 10
            f[f"m_{k}_ret21"] = _broadcast(m21, cols)
            f[f"tilt_{k}"] = _rolling_beta(daily, mret) * _broadcast(m21, cols)

    # ---- sector: momentum of the stock's industry and its strength within it ----
    sec_of = {t: s for s, ts in config.SECTORS.items() for t in ts}
    groups = pd.Series({c: sec_of.get(c, "Other") for c in cols})
    for n, name in [(63, "63"), (21, "21")]:
        r = f[f"ret_{n}"]
        sec_mean = r.T.groupby(groups).transform("mean").T
        f[f"rel_sector_{name}"] = r - sec_mean
        if n == 63:
            f["sector_mom_63"] = sec_mean
            f["rank_sector_mom"] = sec_mean.rank(axis=1, pct=True)

    # ---- company news + world news from GDELT ----
    if gdelt:
        T, V = gdelt["tone"], gdelt["vol"]
        tc = T.reindex(columns=cols)
        vc = V.reindex(columns=cols)
        f["n_tone"] = tc
        f["n_tone_21"] = tc.rolling(21, min_periods=5).mean()
        f["n_tone_shock"] = (tc - tc.rolling(126, min_periods=30).mean()) / tc.rolling(126, min_periods=30).std()
        f["n_attn"] = np.log1p(vc) - np.log1p(vc.rolling(63, min_periods=20).mean())
        f["rank_n_tone_shock"] = f["n_tone_shock"].rank(axis=1, pct=True)
        f["n_tone_x_attn"] = f["n_tone_shock"] * f["n_attn"].clip(lower=0)
        wz = []
        for k in WORLD_QUERIES:
            if k in T.columns:
                z = _z(T[k].rolling(21, min_periods=5).mean())
                f[f"w_{k[2:].lower()}_z"] = _broadcast(z, cols)
                wz.append(z)
        if wz:
            f["w_mood"] = _broadcast(pd.concat(wz, axis=1).mean(axis=1), cols)

    f["news_sent"], f["news_count"] = news.history_frames(idx, cols)

    fwd = close.shift(-config.HORIZON_DAYS) / close - 1
    panel = pd.concat({k: v.reindex(index=idx, columns=cols).stack(future_stack=True) for k, v in f.items()}, axis=1)
    panel["fwd_ret"] = fwd.stack(future_stack=True)
    panel.index.names = ["date", "ticker"]
    med = panel.groupby(level="date")["fwd_ret"].transform("median")
    panel["fwd_excess"] = panel["fwd_ret"] - med
    panel["label"] = np.where(panel["fwd_ret"].isna(), np.nan, (panel["fwd_ret"] > med).astype(float))
    for c in ALL_FEATURES:            # every factor column exists, even if a data source was unavailable
        if c not in panel.columns:
            panel[c] = np.nan
    return panel.replace([np.inf, -np.inf], np.nan)
