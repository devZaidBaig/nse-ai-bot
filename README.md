# NSE AI Paper-Trading Bot 🇮🇳

An AI stock-picking bot for the **Indian market (NIFTY 50)** that trades **₹10,000 of dummy money**.
It uses **live prices and news**, runs **in the cloud on GitHub Actions** (your PC can stay off), and sends you
**WhatsApp / Telegram updates**.

> ⚠️ Paper trading only. No real orders are placed and no broker is connected. Not investment advice.

## What it does each trading day (IST)

| Time | Run | What happens |
|---|---|---|
| 10:05, 11:35, 1:05, 2:15 | **watch** | Checks live prices against each holding's trailing stop and sells if hit. You get a 🚨 message. |
| 3:07 PM | **decide** | Downloads prices (including today's live price), reads the news, retrains the AI on Fridays, trades at live prices, and sends the 📈 daily update. Fridays also include a 🗓️ weekly recap. |
| Sunday 9:17 AM | **backtest** | Re-tests the strategy on the last 2 years with ₹10,000 of dummy money. You get a 🧪 summary. |

NSE holidays are detected automatically: no trades and no messages.

## The AI

1. **Price model:** an ensemble of gradient-boosted trees and logistic regression. It predicts the chance each stock **beats the median NIFTY 50 stock over the next 5 trading days**. It learns from 19 price signals (momentum over 1 week to 12 months, volatility, RSI, trend, drawdown, volume surges, rank against peers, market trend). It is retrained weekly on a rolling 3 years, with no look-ahead.
2. **News model:** for every NIFTY 50 stock it collects headlines from the last 3 days via Google News. **FinBERT**, an AI trained on financial text, scores each one from −1 (bad) to +1 (good).
   - Good news nudges a stock's score up and bad news nudges it down. Strongly negative news (≤ −0.45 with 3+ headlines) blocks a buy.
   - Every day's scores are saved to `state/news_history.csv`, and the price model starts using news as a feature once enough history builds up (roughly 2–3 months). Free historical news archives don't exist, so the bot builds its own.
3. **Portfolio for ₹10,000:** holds the **top 3** affordable picks (≈₹3,300 each, whole shares only). Stocks priced above the per-stock budget are skipped. Leftover cash buys extra shares of the picks. A holding is kept while it stays in the top 12, which avoids paying fees on needless trades.
4. **Risk:** an **8% trailing stop** (sell if the price falls 8% below its highest point since buying). Only 40% of the money is invested when NIFTY is below its 200-day average.
5. **Realistic costs:** 0.1% STT, exchange fees and GST, stamp duty, slippage, and the **₹15.34 DP charge** every time a stock is sold.

**Small-account reality check:** the DP charge is a flat fee, so on ₹10,000 every sell costs about 0.15%. In testing, fees came to roughly 8–10% of the account per year. That's a real drag, and it's why the bot trades sparingly. Fees matter much less on bigger accounts.

## Setup

1. Put these files in a GitHub repo (Claude can do this for you if GitHub is connected to Claude). Any repo works, private or public.
2. *(Only if a run fails with a push/permission error)* Repo **Settings → Actions → General → Workflow permissions → Read and write** → Save.
3. **Messages:** add secrets in **Settings → Secrets and variables → Actions → New repository secret**:
   - **WhatsApp (CallMeBot, free):** open https://www.callmebot.com/blog/free-api-whatsapp-messages/ on your phone and save the bot number shown there (it has been +34 644 71 81 99, but it changes). Send it the WhatsApp message `I allow callmebot to send me messages` and you'll get an API key back. Add the secrets `WHATSAPP_PHONE` = your number with country code and no + (e.g. `919876543210`), and `WHATSAPP_APIKEY` = the key.
     *Note:* CallMeBot is a free hobby service. WhatsApp sometimes blocks it, and it has started charging some users. If messages stop arriving, use Telegram.
   - **Telegram (free and very reliable):** message **@BotFather** → `/newbot` → copy the token. Send your new bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat id. Add the secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
   - You can set up both. The bot sends to every channel that has secrets.
4. **Test messages:** **Actions → Trade → Run workflow → mode: test-message**.
5. **Train it on history:** **Actions → Backtest → Run workflow** (about 3 min).
6. **Start:** **Actions → Trade → Run workflow → mode: decide, force: ✅**. After that it runs by itself.
7. *(Optional)* Dashboard: **Settings → Pages → Deploy from branch → main / docs**. Pages needs a public repo on the free plan; otherwise open `docs/index.html` from the repo.

GitHub's free tier covers this: about 5 short runs per trading day uses roughly 300–400 of the 2,000 free minutes a month on a private repo, and public repos are unlimited.

## Settings

Everything is in `bot/config.py`: starting capital, number of stocks, stop-loss %, news weight, broker fees, stock list.

## Before ever using real money

- Paper trade for **at least 3–6 months** and compare against simply holding a NIFTY 50 index fund.
- A backtest is an optimistic upper bound. The stock list is today's NIFTY 50 (survivorship bias), and Yahoo prices can be a few minutes delayed.
- Since **1 April 2026**, SEBI rules require every automated retail order to go through a SEBI-registered broker's API, carry an exchange-issued **Algo ID**, and use static-IP whitelisting and 2FA. Going live means using your broker's approved API and following its algo onboarding.
