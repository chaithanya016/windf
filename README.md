# Day-Ahead Wind Forecast Desk

Web app that helps a UK utility's day-ahead desk (1) see the latest national wind forecast that was
actually available when the D-1 purchase decision had to be made and (2) quantify how wrong that
forecast tends to be. Scope: Elexon BMRS **FUELHH** (actual WIND) and **WINDFOR** (forecast), delivery days in **January 2026**.

- **Live app:** https://windf-git-main-sher-20d6.vercel.app/
- **Demo video (unlisted):** https://youtu.be/Ho7Xjfx3Tw4?si=_a7pkd7Uq_z2F8Bl

> **AI disclosure:** this project was built with assistance from Claude (Anthropic) for code generation, design and documentation. All logic was reviewed and tested by the author.

## Key idea / analysis

A buyer commits in the day-ahead auction on D-1. For every target half-hour on day D, the only usable
forecast is the **latest run with `publishTime` ≤ gate time on D-1** (default **09:00 UK**, adjustable in the UI;
this is an assumption — set it to your real gate closure). Accuracy is measured on exactly those forecasts.

- Error = forecast − actual (positive = over-forecast → risk of a shortfall; negative = under-forecast → over-buying).
- Metrics: MAE, RMSE, bias, wMAPE, P90/P95 absolute error, error quantiles, error by hour/day/lead time.
- **Uncertainty band** for a day = `forecast − q95(error)` … `forecast − q05(error)`, with quantiles learned **only from earlier days**
  (expanding window, no look-ahead). Day 1 therefore shows no band.
- Wind-only: demand is out of scope, so the app outputs the wind side of "demand − wind = residual to buy".

## Run it

Needs real data first (Elexon API, no key):

```bash
python scripts/fetch_data.py          # writes backend/data/actuals.csv + forecasts.csv; commit them
```
(`scripts/make_sample_data.py` generates **synthetic** data for offline development; the UI shows a banner when it is in use.)

**Docker (single container, API + UI on :8000)**
```bash
docker compose up --build        # http://localhost:8000
```

**Local dev**
```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api)
python -m pytest backend/tests
```

**Deploy to Vercel:** push the repo, import it in Vercel (root directory = repo root). `vercel.json` builds the
React app to static files and serves the FastAPI app as one serverless function at `/api/*`. The data CSVs are
bundled with the function, so no outbound calls are made at request time.

## Layout

```
backend/app/data.py        load CSV snapshot, restrict to Jan 2026
backend/app/analysis.py    decision-forecast selection + all metrics (pure functions)
backend/app/main.py        FastAPI routes: /api/day, /api/accuracy, /api/lead-time, /api/config, /api/health
backend/tests/             unit tests for cut-off logic, error sign, metrics, no-look-ahead band
backend/data/              data snapshot (CSV)
scripts/fetch_data.py      Elexon downloader (stdlib only)
scripts/make_sample_data.py  synthetic data for dev
frontend/src/App.jsx       React UI (Decision view, Accuracy, Lead time) using Recharts
api/index.py               Vercel entrypoint
Dockerfile, docker-compose.yml, vercel.json, requirements.txt
docs/VIDEO_SCRIPT.md       script for the 2-part demo video
```

## Known limitations

- Gate time is an assumed constant; real auction gate closures differ by venue.
- Band uses an unconditional error distribution; errors are larger when wind is high, so a conditional band is a natural next step.
- National totals only; no demand, price or regional data (out of scope).
- Data is a static snapshot; a scheduled refresh job would be needed for production.
