# NSE AI Paper-Trading Bot 🇮🇳

An AI stock-picking bot for the **Indian market (NIFTY 50)** that trades **₹10,000 of dummy money**.
It uses **live prices and news**, runs **in the cloud on GitHub Actions** (your PC can stay off), and sends you
**WhatsApp / Telegram updates**.

> ⚠️ Paper trading only. No real orders are placed and no broker is connected. Not investment advice.

## What it does each trading day (IST)

| Time | Run | What happens |
|---|---|---|
| 10:05, 11:35, 1:05, 2:15 | **watch** | Checks live prices. If a holding is down 7%+ on the day you get a ⚠️ alert (no selling). |
| 3:07 PM | **decide** | Live prices + news. Sends the 📈 daily update. **Every 4 weeks (on a Friday)** it retrains the AI and re-picks stocks. Fridays include a 🗓️ weekly recap. |
| Sunday 9:17 AM | **backtest** | Re-tests the strategy on the last 3 years with ₹10,000 of dummy money. You get a 🧪 summary. |

NSE holidays are detected automatically.

## The AI

1. **Price model:** an ensemble of gradient-boosted trees and logistic regression. It predicts which NIFTY 50 stocks will **beat the median stock over the next month**. It learns from 19 price signals (momentum, volatility, RSI, trend, drawdown, volume, rank against peers, market trend). It is retrained every 4 weeks on a rolling 3 years, with no look-ahead.
2. **News model:** collects Google News headlines from the last 3 days for every stock, and **FinBERT** (a finance-tuned AI) scores each one from −1 to +1. Good news nudges a stock's score up and bad news nudges it down. Strongly negative news blocks a buy. Daily scores are saved to `state/news_history.csv`, and the price model starts using them once a few months of history exist.
3. **Portfolio for ₹10,000:** holds the top 3 affordable picks (whole shares). Leftover cash buys extra shares, and a pick is kept while it stays in the top 12.
4. **Risk:** only 40% of the money is invested when NIFTY is below its 200-day average. There is no trailing stop (see results below).
5. **Realistic costs:** STT, exchange fees and GST, stamp duty, slippage, and the ₹15.34 DP charge on every sell.

## How the strategy was chosen (real NSE data, ₹10,000 dummy money)

Several versions were tested on the same data (`python -m bot.research --set main`; results in `state/research.md`).
The original weekly version earned +15.8% over 3 years against NIFTY's +20.4%: it paid **54% of the account in fees**.
Trading monthly with a 1-month target fixed most of that.
An 8% trailing stop then *hurt* in every period tested, because it sold on normal dips:

| Period ending Oct 2026 | Monthly AI, **no stop** (live) | with 8% stop | with 20% stop | NIFTY |
|---|---|---|---|---|
| 1 year | **+7.0%** | −16.2% | −16.1% | −10.9% |
| 2 years | **+23.5%** | −17.1% | −7.0% | −5.3% |
| 4 years | **+155%** | +48.6% | +132% | +28.0% |

**Read these with healthy skepticism.** The stock list is *today's* NIFTY 50, which favours stocks that did well (survivorship bias). The version was picked after comparing several. The periods overlap. And past results don't predict the future. Expect real performance to be noticeably worse than the backtest. That's what the paper-trading period is for.

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
