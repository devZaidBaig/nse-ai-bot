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

## How the bot learns (weekly, automatic)

**Signals it can use**
- **Price:** momentum, trend, volatility, volume, rank against peers.
- **World markets:** the rupee, crude oil, US 10-year yield, S&P 500, India VIX, gold and the dollar. The bot also uses each stock's measured sensitivity to them, for example how an IT stock tends to react when the rupee weakens.
- **Sector:** sector momentum and the stock's strength within its sector.
- **Company news:** daily tone and attention from **GDELT** (2018 → today), including sudden shocks compared with the company's own normal level. GDELT is a free database of global news.
- **World/India news mood:** coverage of the economy, RBI, Fed, oil, recession, tariffs and conflict.
- **Live headlines:** FinBERT scores on today's headlines, used only as a small nudge until enough history exists to test them.

**Training rules** (`bot/train.py`, results in `state/training_report.md`)
1. Every signal is tested for whether it predicts next month's returns (monthly rank correlation, t-statistics).
2. Groups of signals and model settings are compared **walk-forward**: the model is retrained every quarter using only data available at that point.
3. The best candidates run full ₹10,000 portfolio simulations with real costs.
4. **The most recent 12 months are a holdout.** They are never used to choose anything, only to judge. A new model replaces the live one only if it is at least as good on that unseen year.
5. A "sell on sudden bad company news" rule switches on only if the history shows such news really predicts underperformance and the holdout agrees.

**Schedule:** Claude starts the bot 3× each weekday (10:12 news check, 1:12 price check, 3:12 decision) and retrains it every Sunday at 10:41, then sends a summary.
You can also start runs by editing `run-request.txt` (morning / watch / decide), `lab-request.txt` (train) or `backfill-request.txt` (news downloads) and pushing.

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
   - **WhatsApp (official Meta WhatsApp Cloud API, ≈₹0.12 per message, about ₹4/month):**
     1. Go to **developers.facebook.com** → log in with Facebook → **My Apps → Create app** → use case **"Connect with customers through WhatsApp"** (type *Business*). Create or choose a business portfolio when asked.
     2. In the app open **WhatsApp → API Setup**. Meta gives you a free **test phone number**. Under **"To"**, add **your own WhatsApp number** and confirm the code Meta sends you. Copy the **Phone number ID** shown on this page.
     3. **Create the message template:** go to **WhatsApp Manager** (business.facebook.com → WhatsApp accounts → Message templates) → **Create template** → Category **Utility** → name `trading_update`, language **English** → Body: `Your paper-trading bot update: {{1}}` → sample value: `Value ₹10,050, no trades today` → Submit. Approval usually takes minutes.
     4. **Permanent token:** in **business.facebook.com → Settings → Users → System users** → Add (role Admin) → **Assign assets** → your app (full control) and your WhatsApp account → **Generate new token** for the app with permissions `whatsapp_business_messaging` and `whatsapp_business_management`, expiry **Never**. Copy it. (The temporary token on the API Setup page expires after 24h, so don't use that one.)
     5. **Add a payment method** in WhatsApp Manager → Payment settings, because Meta bills per message. Expect about ₹3–4 a month for this bot.
     6. Add GitHub secrets: `WA_TOKEN` (the permanent token), `WA_PHONE_NUMBER_ID`, and `WA_TO` (your number with country code, digits only, e.g. `919876543210`). If you used a different template name or language, also add `WA_TEMPLATE` / `WA_TEMPLATE_LANG` (e.g. `en_US`).
     Messages arrive on one line with " | " between items, because WhatsApp templates can't contain line breaks.
   - **Telegram (free, 5 minutes, recommended even if you set up WhatsApp):** message **@BotFather** → `/newbot` → copy the token. Send your new bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat id. Add the secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
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
