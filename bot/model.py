"""The 'AI': an ensemble of gradient-boosted trees + logistic regression that ranks stocks
by the probability they beat their peers over the next month. Which factors it uses and its
settings come from state/model_config.json, chosen by the training pipeline (bot/train.py)."""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config
from .features import FEATURES

DEFAULT_CONFIG = {"features": FEATURES, "params": {"max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 200,
                                                   "max_iter": 200, "l2": 1.0, "C": 0.1, "w_gbm": 0.6},
                  "news_exit": None, "name": "default (price factors only)"}
_override = None


def _merge(cfg):
    return {**DEFAULT_CONFIG, **cfg, "params": {**DEFAULT_CONFIG["params"], **cfg.get("params", {})}}


def active_config() -> dict:
    """The model setup the bot trades with: a temporary override (during training), else the saved champion."""
    if _override is not None:
        return _override
    try:
        cfg = json.loads(config.MODEL_CONFIG.read_text())
        return {**DEFAULT_CONFIG, **cfg, "params": {**DEFAULT_CONFIG["params"], **cfg.get("params", {})}}
    except Exception:
        return DEFAULT_CONFIG


def set_override(cfg):
    global _override
    _override = None if cfg is None else {**DEFAULT_CONFIG, **cfg, "params": {**DEFAULT_CONFIG["params"], **cfg.get("params", {})}}


class Ranker:
    def __init__(self, cfg=None):
        cfg = _merge(cfg) if cfg else active_config()
        p = cfg["params"]
        self.features = list(cfg["features"])
        self.w_gbm = p["w_gbm"]
        self.gbm = HistGradientBoostingClassifier(
            max_iter=p["max_iter"], learning_rate=p["learning_rate"], max_depth=p["max_depth"],
            min_samples_leaf=p["min_samples_leaf"], l2_regularization=p["l2"], random_state=0,
        )
        self.lin = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                                 LogisticRegression(C=p["C"], max_iter=500))
        self.trained_on = None

    def fit(self, panel: pd.DataFrame, as_of: pd.Timestamp):
        """Train only on rows whose label was fully known by `as_of` (no look-ahead)."""
        dates = panel.index.get_level_values("date").unique().sort_values()
        dates = dates[dates <= as_of]
        if len(dates) <= config.HORIZON_DAYS + 252:
            raise ValueError("not enough history to train")
        last_label_date = dates[-(config.HORIZON_DAYS + 1)]
        first = last_label_date - pd.DateOffset(years=config.TRAIN_YEARS)
        d = panel.index.get_level_values("date")
        train = panel[(d >= first) & (d <= last_label_date)].dropna(subset=["label"])
        feats = [c for c in self.features if c in panel.columns]
        train = train[train[feats].notna().mean(axis=1) >= 0.6]
        # Use a factor only if it has enough history in this training window
        self.cols = [c for c in feats if train[c].notna().mean() >= 0.3]
        X, y = train[self.cols].to_numpy(), train["label"].to_numpy()
        self.gbm.fit(X, y)
        self.lin.fit(X, y)
        self.trained_on = (str(first.date()), str(last_label_date.date()), len(train), len(self.cols))
        return self

    def score(self, rows: pd.DataFrame) -> pd.Series:
        X = rows[self.cols].to_numpy()
        p = self.w_gbm * self.gbm.predict_proba(X)[:, 1] + (1 - self.w_gbm) * self.lin.predict_proba(X)[:, 1]
        return pd.Series(p, index=rows.index.get_level_values("ticker"), name="proba")


def apply_news(scores: pd.Series, news: pd.DataFrame | None) -> tuple[pd.Series, set]:
    """Nudge model scores with today's news sentiment; return (adjusted scores, vetoed tickers)."""
    if news is None or news.empty:
        return scores, set()
    sent = news["sentiment"].reindex(scores.index).fillna(0.0)
    cnt = news["count"].reindex(scores.index).fillna(0)
    adj = scores + config.NEWS_WEIGHT * sent * (cnt > 0)
    veto = set(sent[(sent <= config.NEWS_VETO) & (cnt >= 3)].index)
    return adj, veto


def target_weights(scores: pd.Series, risk_on: bool, held=(), prices=None, equity=None, veto=()) -> pd.Series:
    """Pick the top-N stocks above the confidence threshold, equal-weight, capped, regime-scaled.
    - Stocks already held are kept while they stay inside the top HOLD_BUFFER ranks (cuts churn & fees).
    - New picks must be affordable: at least 1 whole share fits in the per-stock budget.
    - Stocks with strongly negative news are not bought."""
    exposure = 1.0 if risk_on else config.RISK_OFF_EXPOSURE
    w = min(exposure / config.TOP_N, config.MAX_POSITION_WEIGHT)
    ranked = scores.sort_values(ascending=False)
    keep = [t for t in ranked.index[:config.HOLD_BUFFER] if t in held and ranked[t] >= 0.5][:config.TOP_N]

    def affordable(t):
        return prices is None or equity is None or (prices.get(t, float("inf")) <= w * equity)

    fresh = [t for t in ranked[ranked >= config.MIN_PROBA].index
             if t not in keep and t not in veto and affordable(t)]
    picks = keep + fresh[:config.TOP_N - len(keep)]
    if not picks:
        return pd.Series(dtype=float)
    return pd.Series(w, index=picks)
