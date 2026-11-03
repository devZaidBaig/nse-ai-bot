"""Historical + live news tone and attention from GDELT (free global news database, 2017→today).

For every company and a set of world/India macro topics we keep a daily time series of:
  tone  – average tone of matching articles (negative = bad news, positive = good news)
  vol   – share of all world news coverage that mentions it (attention)
Cached in state/data/gdelt/<key>.csv and updated incrementally."""
import io
import json
import os
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from . import config

API = "https://api.gdeltproject.org/api/v2/doc/doc"
CACHE = config.STATE_DIR / "data" / "gdelt"
UA = {"User-Agent": "nse-ai-paper-bot/1.0 (research)"}
PAUSE = float(os.environ.get("GDELT_PAUSE", "5.5"))   # GDELT asks for ~1 request / 5 s

# Unambiguous search phrases (short tickers like "ITC" or "LT" would match unrelated news)
COMPANY_QUERIES = {
    "ADANIENT": '"Adani Enterprises"', "ADANIPORTS": '"Adani Ports"', "APOLLOHOSP": '"Apollo Hospitals"',
    "ASIANPAINT": '"Asian Paints"', "AXISBANK": '"Axis Bank"', "BAJAJ-AUTO": '"Bajaj Auto"',
    "BAJFINANCE": '"Bajaj Finance"', "BAJAJFINSV": '"Bajaj Finserv"', "BEL": '"Bharat Electronics"',
    "BHARTIARTL": '"Bharti Airtel"', "CIPLA": '"Cipla"', "COALINDIA": '"Coal India"', "DRREDDY": '"Dr Reddy\'s"',
    "EICHERMOT": '"Eicher Motors"', "ETERNAL": '(Zomato OR "Eternal Ltd")', "GRASIM": '"Grasim"',
    "HCLTECH": '"HCL Technologies"', "HDFCBANK": '"HDFC Bank"', "HDFCLIFE": '"HDFC Life"',
    "INDIGO": '("IndiGo" airline OR InterGlobe)', "HINDALCO": '"Hindalco"', "HINDUNILVR": '"Hindustan Unilever"',
    "ICICIBANK": '"ICICI Bank"', "MAXHEALTH": '"Max Healthcare"', "INFY": '"Infosys"', "ITC": '"ITC Limited"',
    "JIOFIN": '"Jio Financial"', "JSWSTEEL": '"JSW Steel"', "KOTAKBANK": '"Kotak Mahindra"',
    "LT": '"Larsen & Toubro"', "M&M": '"Mahindra & Mahindra"', "MARUTI": '"Maruti Suzuki"',
    "NESTLEIND": '"Nestle India"', "NTPC": '"NTPC"', "ONGC": '"ONGC"', "POWERGRID": '"Power Grid Corporation"',
    "RELIANCE": '"Reliance Industries"', "SBILIFE": '"SBI Life"', "SBIN": '"State Bank of India"',
    "SHRIRAMFIN": '"Shriram Finance"', "SUNPHARMA": '"Sun Pharma"', "TATACONSUM": '"Tata Consumer"',
    "TMPV": '"Tata Motors"', "TATASTEEL": '"Tata Steel"', "TCS": '"Tata Consultancy"',
    "TECHM": '"Tech Mahindra"', "TITAN": '"Titan Company"', "TRENT": '"Trent Ltd"',
    "ULTRACEMCO": '"UltraTech Cement"', "WIPRO": '"Wipro"',
}

# World / India macro news topics
WORLD_QUERIES = {
    "W_INDIA_ECON": '"Indian economy"',
    "W_RBI": '"Reserve Bank of India"',
    "W_INDIA_MKT": '(Sensex OR Nifty)',
    "W_FED": '"Federal Reserve"',
    "W_OIL": '"oil prices"',
    "W_RECESSION": 'recession',
    "W_TARIFF": 'tariffs',
    "W_CONFLICT": '(war OR "military strike")',
}


def _get(params, retries=8):
    """GDELT rate-limits shared cloud IPs hard (HTTP 429), so back off patiently."""
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(retries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            time.sleep(PAUSE)
            return raw.decode("utf-8", errors="ignore")
        except Exception as e:
            wait = min(30 * (k + 1), 180)
            print(f"[gdelt] {e.__class__.__name__} ({str(e)[:60]}); retry {k + 1}/{retries} in {wait}s")
            time.sleep(wait)
    return ""


def _timeline(query, mode, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Daily series for one query/mode between start and end."""
    txt = _get({"query": query, "mode": mode, "format": "csv",
                "startdatetime": start.strftime("%Y%m%d000000"),
                "enddatetime": end.strftime("%Y%m%d235959"),
                "timelinesmooth": 0})
    if not txt or "Date" not in txt[:200]:
        if txt:
            print(f"[gdelt] unexpected reply for {query} {mode}: {txt[:120]!r}")
        return pd.Series(dtype=float)
    df = pd.read_csv(io.StringIO(txt))
    # CSV columns: Date, Series, Value
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str[:10], errors="coerce")
    if "Series" in df.columns and df["Series"].nunique() > 1:
        # timelinevolraw returns two series: matching "Article Count" and "Total Monitored Articles"
        keep = [x for x in df["Series"].unique() if "count" in str(x).lower() and "total" not in str(x).lower()]
        df = df[df["Series"] == (keep[0] if keep else df["Series"].iloc[0])]
    s = df.dropna(subset=["Date"]).groupby("Date")["Value"].mean()
    return s


def update(keys=None, start="2018-01-01", chunk_years=10, max_minutes=None):
    """Fill/refresh the cache. First run backfills from `start`; later runs only fetch recent days."""
    CACHE.mkdir(parents=True, exist_ok=True)
    allq = {**COMPANY_QUERIES, **WORLD_QUERIES}
    if not keys:
        def _need(k):
            f = CACHE / f"{k.replace('&', 'and')}.csv"
            if not f.exists():
                return 0
            return 1 if pd.read_csv(f)["vol"].isna().mean() > 0.5 else 2
        keys = sorted(allq, key=_need)
    today = pd.Timestamp.now(tz="Asia/Kolkata").normalize().tz_localize(None)
    t0 = time.time()
    for key in keys:
        if max_minutes and (time.time() - t0) / 60 > max_minutes:
            print(f"[gdelt] time budget reached; remaining keys next run")
            break
        f = CACHE / f"{key.replace('&', 'and')}.csv"
        old = pd.read_csv(f, parse_dates=["date"], index_col="date") if f.exists() else pd.DataFrame()
        s0 = (old.index.max() - pd.Timedelta(days=5)) if len(old) else pd.Timestamp(start)
        # Repair: a series whose attention (volume) history failed earlier gets it re-downloaded in full
        if len(old) and old["vol"].isna().mean() > 0.5:
            v = _timeline(allq[key], "timelinevolraw", pd.Timestamp(start), today)
            if len(v):
                old["vol"] = v.reindex(old.index)
                print(f"[gdelt] {key}: repaired attention history ({v.notna().sum()} days)")
        frames = []
        cur = s0
        while cur <= today:
            nxt = min(cur + pd.DateOffset(years=chunk_years) - pd.Timedelta(days=1), today)
            tone = _timeline(allq[key], "timelinetone", cur, nxt)
            vol = _timeline(allq[key], "timelinevolraw", cur, nxt)
            if len(tone) or len(vol):
                frames.append(pd.DataFrame({"tone": tone, "vol": vol}))
            cur = nxt + pd.Timedelta(days=1)
        if frames:
            new = pd.concat(frames)
            df = pd.concat([old[~old.index.isin(new.index)], new]).sort_index() if len(old) else new.sort_index()
            df.index.name = "date"
            df.round(4).to_csv(f)
            print(f"[gdelt] {key}: {len(df)} days ({df.index.min().date()} → {df.index.max().date()})")
        else:
            print(f"[gdelt] {key}: no data returned")


def load(columns, index) -> dict:
    """Return {'tone': DataFrame, 'vol': DataFrame} [date x key] aligned to trading-day index (NaN if missing)."""
    out = {}
    if os.environ.get("BOT_SYNTHETIC") == "1":
        rng = np.random.default_rng(3)
        keys = list(columns) + list(WORLD_QUERIES)
        out["tone"] = pd.DataFrame(rng.normal(-0.5, 1.5, (len(index), len(keys))), index=index, columns=keys)
        out["vol"] = pd.DataFrame(rng.lognormal(3, 0.6, (len(index), len(keys))), index=index, columns=keys)
        return out
    tone, vol = {}, {}
    for key in list(columns) + list(WORLD_QUERIES):
        f = CACHE / f"{key.replace('&', 'and')}.csv"
        if f.exists():
            d = pd.read_csv(f, parse_dates=["date"], index_col="date")
            # News published on non-trading days is carried to the next trading day (no look-ahead)
            tone[key] = d["tone"].resample("D").mean()
            vol[key] = d["vol"].resample("D").sum(min_count=1)
    if not tone:
        return {}
    T = pd.DataFrame(tone)
    V = pd.DataFrame(vol)
    # Use only news up to the previous calendar day for each trading day (decisions happen before close)
    T = T.shift(1).rolling(3, min_periods=1).mean().reindex(index, method="ffill")
    V = V.shift(1).rolling(3, min_periods=1).sum().reindex(index, method="ffill")
    return {"tone": T, "vol": V}


def probe():
    """Check how far back GDELT timelines go and how fast we may query."""
    rep = {}
    for start, end in [("2017-01-01", "2017-03-31"), ("2019-06-01", "2019-06-30"), ("2023-01-01", "2024-12-31"),
                       ("2026-10-01", None)]:
        e = pd.Timestamp(end) if end else pd.Timestamp.now().normalize()
        t = time.time()
        s = _timeline('"Reliance Industries"', "timelinetone", pd.Timestamp(start), e)
        rep[f"{start}→{e.date()}"] = {"days": int(len(s)), "first": str(s.index.min().date()) if len(s) else None,
                                      "last": str(s.index.max().date()) if len(s) else None,
                                      "mean_tone": round(float(s.mean()), 3) if len(s) else None,
                                      "secs": round(time.time() - t, 1)}
    print(json.dumps(rep, indent=1))
    return rep


def redownload_vol(keys, start="2018-01-01"):
    """Re-fetch only the attention (article count) history for the given series."""
    allq = {**COMPANY_QUERIES, **WORLD_QUERIES}
    today = pd.Timestamp.now(tz="Asia/Kolkata").normalize().tz_localize(None)
    for key in keys:
        f = CACHE / f"{key.replace('&', 'and')}.csv"
        if not f.exists():
            continue
        old = pd.read_csv(f, parse_dates=["date"], index_col="date")
        v = _timeline(allq[key], "timelinevolraw", pd.Timestamp(start), today)
        if len(v):
            old["vol"] = v.reindex(old.index)
            old.round(4).to_csv(f)
            print(f"[gdelt] {key}: attention re-downloaded ({v.notna().sum()} days, median {v.median():.0f} articles/day)")
        else:
            print(f"[gdelt] {key}: attention download failed")
