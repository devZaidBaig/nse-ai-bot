"""News sentiment: recent Google News headlines per stock, scored by FinBERT (a finance-tuned AI model).

Every run's scores are appended to state/news_history.csv, so the price model can gradually learn
how news relates to returns as history builds up (free historical news archives don't exist)."""
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd

from . import config

HISTORY = config.STATE_DIR / "news_history.csv"
UA = {"User-Agent": "Mozilla/5.0 (compatible; nse-ai-paper-bot/1.0)"}

# Fallback scorer if FinBERT can't load (keeps the bot running no matter what)
POS = set("surge surges soar soars jump jumps rally rallies gain gains rise rises record beat beats strong upgrade upgrades "
          "outperform profit profits growth bullish buy wins win order orders expansion boost boosts high highs positive "
          "approval approves dividend bonus robust upbeat raises raised".split())
NEG = set("fall falls drop drops plunge plunges slump slumps crash crashes decline declines loss losses weak downgrade "
          "downgrades underperform bearish sell probe fraud penalty fine fined lawsuit cut cuts low lows negative miss misses "
          "warning concern concerns resign resigns raid default slowdown pressure tumbles tumble sinks sink".split())


def _fetch(ticker: str) -> list[str]:
    q = f'"{config.NAMES.get(ticker, ticker)}" share when:{config.NEWS_LOOKBACK_DAYS}d'
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    try:
        xml = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15).read()
        items = ET.fromstring(xml).findall("./channel/item")
    except Exception as e:
        print(f"[news] {ticker}: fetch failed ({e.__class__.__name__})")
        return []
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=config.NEWS_LOOKBACK_DAYS)
    out = []
    for it in items:
        title = (it.findtext("title") or "").rsplit(" - ", 1)[0].strip()   # drop " - Publisher"
        try:
            if pd.Timestamp(parsedate_to_datetime(it.findtext("pubDate"))) < cutoff:
                continue
        except Exception:
            pass
        if title and title not in out:
            out.append(title)
    return out[: config.NEWS_MAX_HEADLINES]


class _Scorer:
    def __init__(self):
        self.pipe = None
        if os.environ.get("BOT_SENTIMENT", "finbert") == "finbert":
            try:
                from transformers import pipeline
                self.pipe = pipeline("text-classification", model=config.SENTIMENT_MODEL, top_k=None, truncation=True)
                print(f"[news] using {config.SENTIMENT_MODEL}")
            except Exception as e:
                print(f"[news] FinBERT unavailable ({e.__class__.__name__}); using keyword scorer")

    def __call__(self, texts: list[str]) -> list[float]:
        if not texts:
            return []
        if self.pipe is not None:
            res = self.pipe(texts, batch_size=32)
            out = []
            for r in res:
                d = {x["label"].lower(): x["score"] for x in r}
                out.append(d.get("positive", 0.0) - d.get("negative", 0.0))
            return out
        out = []
        for t in texts:
            words = re.findall(r"[a-z]+", t.lower())
            p, n = sum(w in POS for w in words), sum(w in NEG for w in words)
            out.append(0.0 if p + n == 0 else (p - n) / (p + n))
        return out


def today_sentiment(tickers, date) -> pd.DataFrame:
    """DataFrame indexed by ticker: sentiment (-1..+1), count, headline (most extreme one)."""
    if os.environ.get("BOT_SYNTHETIC") == "1":
        rng = np.random.default_rng(abs(hash(str(date))) % 2**32)
        df = pd.DataFrame({"sentiment": rng.normal(0, 0.3, len(tickers)).clip(-1, 1),
                           "count": rng.integers(0, 10, len(tickers)),
                           "headline": "(synthetic test headline)"}, index=list(tickers))
    else:
        with ThreadPoolExecutor(8) as ex:
            heads = dict(zip(tickers, ex.map(_fetch, tickers)))
        scorer = _Scorer()
        rows = {}
        for t, hs in heads.items():
            s = scorer(hs)
            if s:
                i = int(np.argmax(np.abs(s)))
                rows[t] = dict(sentiment=float(np.mean(s)), count=len(s), headline=hs[i])
            else:
                rows[t] = dict(sentiment=0.0, count=0, headline="")
        df = pd.DataFrame.from_dict(rows, orient="index")
    _append_history(df, date)
    return df


def _append_history(df: pd.DataFrame, date):
    h = df[["sentiment", "count"]].copy()
    h.insert(0, "date", str(pd.Timestamp(date).date()))
    h.index.name = "ticker"
    h = h.reset_index()
    if HISTORY.exists():
        old = pd.read_csv(HISTORY)
        old = old[old["date"] != h["date"].iloc[0]]          # re-runs overwrite the same day
        h = pd.concat([old, h], ignore_index=True)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    h.round(4).to_csv(HISTORY, index=False)


def history_frames(index: pd.DatetimeIndex, columns) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Past sentiment as [date x ticker] frames (3-day average), NaN where no news was recorded."""
    empty = pd.DataFrame(np.nan, index=index, columns=columns)
    if not HISTORY.exists():
        return empty, empty.copy()
    h = pd.read_csv(HISTORY, parse_dates=["date"])
    sent = h.pivot_table(index="date", columns="ticker", values="sentiment").reindex(columns=columns)
    cnt = h.pivot_table(index="date", columns="ticker", values="count").reindex(columns=columns)
    sent = sent.reindex(index).rolling(3, min_periods=1).mean()
    cnt = cnt.reindex(index).rolling(3, min_periods=1).sum()
    return sent, cnt
