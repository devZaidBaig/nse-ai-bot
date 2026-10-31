"""Turn prices into features the model learns from, plus the label it predicts."""
import numpy as np
import pandas as pd

from . import config, news

FEATURES = [
    "ret_5", "ret_10", "ret_21", "ret_63", "ret_126", "mom_12_1",
    "vol_21", "vol_63", "rsi_14", "dist_sma50", "dist_sma200", "drawdown_252",
    "volume_ratio", "rank_ret_21", "rank_ret_63", "rank_mom_12_1", "rank_vol_21",
    "mkt_ret_21", "mkt_above_sma200",
    "news_sent", "news_count",          # empty at first; the model learns from them as news history builds up
]


def _rsi(close: pd.DataFrame, n=14) -> pd.DataFrame:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / down.replace(0, np.nan))


def build(close: pd.DataFrame, volume: pd.DataFrame, bench: pd.Series) -> pd.DataFrame:
    """Long panel indexed by (date, ticker) with FEATURES, 'fwd_ret' and 'label'."""
    daily = close.pct_change(fill_method=None)
    f = {
        "ret_5": close.pct_change(5, fill_method=None),
        "ret_10": close.pct_change(10, fill_method=None),
        "ret_21": close.pct_change(21, fill_method=None),
        "ret_63": close.pct_change(63, fill_method=None),
        "ret_126": close.pct_change(126, fill_method=None),
        "mom_12_1": close.shift(21) / close.shift(252) - 1,     # classic 12-minus-1-month momentum
        "vol_21": daily.rolling(21).std() * np.sqrt(252),
        "vol_63": daily.rolling(63).std() * np.sqrt(252),
        "rsi_14": _rsi(close),
        "dist_sma50": close / close.rolling(50).mean() - 1,
        "dist_sma200": close / close.rolling(200).mean() - 1,
        "drawdown_252": close / close.rolling(252).max() - 1,
        "volume_ratio": volume.rolling(5).mean() / volume.rolling(63).mean(),
    }
    for k in ["ret_21", "ret_63", "mom_12_1", "vol_21"]:
        f[f"rank_{k}"] = f[k].rank(axis=1, pct=True)            # relative strength vs peers

    b = bench.reindex(close.index).ffill()
    mkt_ret = b.pct_change(21, fill_method=None)
    mkt_up = (b > b.rolling(config.REGIME_SMA).mean()).astype(float)
    f["mkt_ret_21"] = pd.DataFrame({c: mkt_ret for c in close.columns})
    f["mkt_above_sma200"] = pd.DataFrame({c: mkt_up for c in close.columns})
    f["news_sent"], f["news_count"] = news.history_frames(close.index, close.columns)

    fwd = close.shift(-config.HORIZON_DAYS) / close - 1
    panel = pd.concat({k: v.stack(future_stack=True) for k, v in f.items()}, axis=1)
    panel["fwd_ret"] = fwd.stack(future_stack=True)
    panel.index.names = ["date", "ticker"]
    # Label: did this stock beat the median stock over the next HORIZON_DAYS?
    med = panel.groupby(level="date")["fwd_ret"].transform("median")
    panel["label"] = np.where(panel["fwd_ret"].isna(), np.nan, (panel["fwd_ret"] > med).astype(float))
    return panel.replace([np.inf, -np.inf], np.nan)
