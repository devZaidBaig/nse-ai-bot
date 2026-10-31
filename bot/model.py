"""The 'AI': an ensemble of gradient-boosted trees + logistic regression that ranks stocks
by the probability they outperform their peers over the next week."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config
from .features import FEATURES


class Ranker:
    def __init__(self):
        self.gbm = HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_depth=4, min_samples_leaf=200,
            l2_regularization=1.0, random_state=0,
        )
        self.lin = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                 LogisticRegression(C=0.1, max_iter=500))
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
        train = train[train[FEATURES].notna().sum(axis=1) >= len(FEATURES) - 5]  # news features may be missing
        # Use a feature only once it has enough history (news features start empty and fill up over time)
        self.cols = [c for c in FEATURES if train[c].notna().mean() >= 0.05]
        X, y = train[self.cols].to_numpy(), train["label"].to_numpy()
        self.gbm.fit(X, y)
        self.lin.fit(X, y)
        self.trained_on = (str(first.date()), str(last_label_date.date()), len(train), len(self.cols))
        return self

    def score(self, rows: pd.DataFrame) -> pd.Series:
        X = rows[self.cols].to_numpy()
        p = 0.6 * self.gbm.predict_proba(X)[:, 1] + 0.4 * self.lin.predict_proba(X)[:, 1]
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
