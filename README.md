# 📈 Penny Stock Tracker

A fully automated penny stock dashboard. Runs entirely on GitHub. **No server, no install, no hosting fees.** GitHub Actions harvests market data hourly; GitHub Pages serves the dashboard.

> ⚠️ **Reality check:** This shows real market data and technical signals. It does **NOT** predict winners. Penny stocks are volatile and often manipulated. Most retail day-traders lose money long-term. Educational tool only. Not financial advice.

---

## 🚀 Deployment — Follow These Steps EXACTLY

Skipping any step = broken dashboard. The order matters. Read carefully.

### ➊ Create the GitHub Repository

1. Go to **https://github.com/new**
2. Repository name: anything you want (e.g. `penny-stocks`)
3. **Visibility: ✅ Public** ← required for free Pages + Actions
4. **Do NOT check** "Add a README file"
5. **Do NOT check** "Add .gitignore"
6. Click **Create repository**

### ➋ Upload the Files

1. Unzip this project on your computer. You should see this structure:
   ```
   penny-stock-tracker/
   ├── .github/
   ├── docs/
   ├── harvester/
   ├── .gitignore
   └── README.md
   ```
2. On your new empty repo page, click **"uploading an existing file"** (it's a link in the middle of the page)
3. **Important:** Open the `penny-stock-tracker` folder and drag the **CONTENTS** (not the folder itself) into the upload area. You should be uploading: `.github`, `docs`, `harvester`, `.gitignore`, `README.md`
4. Scroll down → write commit message (or leave default) → click **Commit changes**
5. After upload, your repo's top-level should show:
   ```
   .github   docs   harvester   .gitignore   README.md
   ```
   If you see a `penny-stock-tracker` folder containing those instead, you uploaded one level too deep. Delete everything and re-upload the contents only.

### ➌ Enable GitHub Actions Write Permission ⚠️ DO THIS BEFORE STEP 4

1. In your repo, click **Settings** (top menu)
2. Left sidebar: **Actions** → **General**
3. Scroll to **Workflow permissions** at the bottom
4. Select **● Read and write permissions** (the radio button)
5. Click **Save**

❗ If you skip this, the workflow will fail with "Permission denied" when trying to commit data.

### ➍ Enable GitHub Pages — POINT TO THE `/docs` FOLDER ⚠️ THIS IS THE STEP THAT TRIPS PEOPLE UP

1. In your repo, click **Settings**
2. Left sidebar: **Pages**
3. Under **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - You'll see two dropdowns next to "Branch":
     - **Left dropdown**: `main`
     - **Right dropdown**: ⚠️ **change from `/ (root)` to `/docs`** ⚠️
   - The right dropdown is THE critical setting. If left at `/ (root)`, GitHub will show the README instead of the dashboard.
4. Click **Save**

A box will appear at the top saying "Your site is live at https://YOUR-USERNAME.github.io/REPO-NAME/" once it deploys (~1 minute).

### ➎ Trigger the First Harvest

The dashboard will load but show "loading data…" until the harvester runs. Run it manually once to populate data:

1. Click the **Actions** tab (top of repo)
2. If you see a banner asking to enable workflows, click **"I understand my workflows, go ahead and enable them"**
3. Left sidebar: click **"Hourly Stock Data Harvest"**
4. Right side: click the **"Run workflow"** dropdown button → click the green **"Run workflow"** button
5. Wait ~2 minutes (refresh page to see progress; green checkmark = done)
6. Refresh your dashboard URL — real data should appear

From this point forward, the harvester runs automatically every hour Monday–Friday.

---

## ✅ Verification Checklist

After all 5 steps, verify each is correct:

| Check | How |
|---|---|
| Files uploaded correctly | Repo root has `docs/`, `harvester/`, `.github/` folders (not nested inside another folder) |
| Pages enabled with `/docs` | Settings → Pages → shows "Your site is live at..." with `/docs` selected as folder |
| Write permissions on | Settings → Actions → General → "Read and write permissions" selected |
| Workflow ran successfully | Actions tab → "Hourly Stock Data Harvest" → green checkmark on latest run |
| Dashboard loads dashboard (not README) | Your `.github.io` URL shows DARK background with "PENNY•TRACKER" header |

If the dashboard URL shows the README (white background, text), the **`/docs` folder setting in Step 4 wasn't saved**. Go back to Settings → Pages and check it.

---

## 📊 Dashboard Tabs

- **📊 Scanner** — Universe tickers ranked by heuristic day-trade score
- **🌅 Pre-Market** — Tickers gapping in extended hours + Finviz top movers
- **📰 News & Catalysts** — Headlines auto-tagged bullish/bearish/catalyst
- **⭐ Watchlist** — Your own tickers (saved in browser localStorage)
- **📓 Trade Journal** — Log trades, see P&L and win rate
- **ℹ About** — Scoring formula and disclaimers

---

## 🗂 What's in This Project

```
penny-stock-tracker/
├── .github/workflows/
│   └── harvest.yml          ← Runs hourly. Edit cron schedule here.
├── harvester/
│   ├── harvest.py           ← Python data scraper. Edit UNIVERSE here.
│   └── requirements.txt     ← Python deps
├── docs/                    ← Served by GitHub Pages
│   ├── index.html           ← The dashboard
│   └── data/                ← JSON files (auto-updated hourly)
│       ├── scan.json
│       ├── premarket.json
│       ├── news.json
│       └── status.json
├── .gitignore
└── README.md
```

---

## ⚙️ Customization

### Add your own tickers to the scanner
Edit `harvester/harvest.py`, find the `UNIVERSE` list near the top, add/remove tickers, commit. Next harvest will use the new list.

### Change harvest frequency
Edit `.github/workflows/harvest.yml`, change the `cron` line:
- Every hour Mon-Fri (default): `'0 * * * 1-5'`
- Every 30 min: `'*/30 * * * 1-5'`
- Every 15 min: `'*/15 * * * 1-5'` (uses more Actions minutes)
- Once daily at 8am ET: `'0 13 * * 1-5'`

GitHub free tier: 2,000 Actions minutes/month for public repos. Hourly schedule uses ~30 min/month.

### Better news data (optional)
1. Sign up free at https://finnhub.io for an API key
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `FINNHUB_API_KEY` · Value: your key
4. Save. The harvester will use it automatically.

### Change scan filters
Edit `harvester/harvest.py`:
- `MAX_PRICE = 10.0` — max stock price to include
- `MIN_VOLUME = 100_000` — minimum daily volume

---

## 🆘 Troubleshooting

**Dashboard URL shows the README, not the dashboard**
→ Settings → Pages → folder dropdown is still `/ (root)`. Change to `/docs` and save.

**Dashboard loads but stuck on "loading data…"**
→ The harvester hasn't run yet. Actions tab → Hourly Stock Data Harvest → Run workflow.

**Workflow fails with "Permission denied" or "403"**
→ Settings → Actions → General → Workflow permissions → Read and write permissions.

**Workflow runs but commits nothing**
→ Check the workflow logs (Actions tab → click the run). yfinance can rate-limit; reduce the `UNIVERSE` size.

**Pre-Market tab is empty**
→ Pre-market is 4:00–9:30am ET, Mon-Fri only. Outside that window this tab is empty by design.

**Some watchlist tickers don't show in scan**
→ They didn't pass the price/volume filter on that harvest. The watchlist tab shows them in a separate section.

---

## 📈 How the Score Works (Heuristic, NOT a Prediction)

| Signal | Points |
|---|---|
| Relative volume > 2× | +25 |
| Relative volume > 1.3× | +10 |
| Gap > 5% | +15 |
| RSI < 30 (oversold) | +15 |
| RSI > 70 (overbought) | +10 |
| Uptrend (price > MA20, MA5 > MA20) | +10 |
| ATR > 8% (high volatility) | +10 |
| Price under $5 | +5 |

Max ≈ 100. Score ≥ 50 = high interest, 25–49 = medium, < 25 = quiet.

This surfaces tickers matching conditions day-traders typically scan for. **It is not a buy signal.** The decision to trade is yours.

---

## ⚠️ Honest Disclaimers

- No algorithm reliably predicts tomorrow's prices. If one existed, it wouldn't be on GitHub.
- Penny stocks are favorite pump-and-dump targets. High score does not equal legitimate move.
- Long-term studies show under 20% of retail day-traders are profitable.
- This is educational software. **Not financial advice.** Trade only what you can afford to lose.

## License

MIT
