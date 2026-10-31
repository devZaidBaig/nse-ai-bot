import numpy as np
import pandas as pd


def summarize(equity: pd.Series, bench: pd.Series, trades: list) -> dict:
    equity, bench = equity.dropna(), bench.reindex(equity.index).ffill()
    r = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    b_cagr = (bench.iloc[-1] / bench.iloc[0]) ** (1 / years) - 1
    sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    dd = (equity / equity.cummax() - 1).min()
    b_dd = (bench / bench.cummax() - 1).min()
    sells = [t for t in trades if t["side"] == "SELL"]
    wins = sum(1 for t in sells if t["pnl"] > 0)
    return {
        "start": str(equity.index[0].date()), "end": str(equity.index[-1].date()),
        "total_return_pct": round(100 * (equity.iloc[-1] / equity.iloc[0] - 1), 2),
        "nifty_return_pct": round(100 * (bench.iloc[-1] / bench.iloc[0] - 1), 2),
        "cagr_pct": round(100 * cagr, 2), "nifty_cagr_pct": round(100 * b_cagr, 2),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown_pct": round(100 * dd, 2), "nifty_max_drawdown_pct": round(100 * b_dd, 2),
        "trades": len(trades), "closed_trades": len(sells),
        "win_rate_pct": round(100 * wins / len(sells), 1) if sells else None,
        "total_fees": round(sum(t["fees"] for t in trades), 2),
    }
