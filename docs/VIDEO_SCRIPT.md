# Video script (≤ 10 min total) — record screen + voice-over, upload as UNLISTED on YouTube

Before recording: use REAL data (`scripts/fetch_data.py`), open the deployed app, pick an interesting day
(e.g. one with a big miss) and note actual numbers from the Accuracy tab to read out.

## Part 1 — Client pitch (≈ 4:30)
| Time | Show | Say |
|---|---|---|
| 0:00–0:30 | Decision view, a day selected | "Every morning your desk commits tomorrow's power. The biggest swing factor is wind — and you only get one shot at the forecast before the gate closes." |
| 0:30–1:30 | KPI cards + chart | "This shows exactly the forecast available at 09:00 on D-1: how many MWh of wind to expect, peak and trough, and when that forecast was published. The shaded band is how far wind actually landed from forecast 90% of the time in earlier days — so you size thermal purchases against a range, not a guess." |
| 1:30–2:30 | Pick a day with large error, show actual line | "Here's a day where wind came in well below forecast. The band flagged this risk." |
| 2:30–3:30 | Accuracy tab | "Over January: MAE X MW, bias Y MW, 95% of misses under Z MW. Error is worst at [hour]." Interpret the bias: over-forecast → shortfall risk. |
| 3:30–4:10 | Lead-time tab | "Forecasts improve markedly as delivery nears — useful for intraday follow-up." |
| 4:10–4:30 | Close | "Pilot result: a quantified, auditable view of wind uncertainty. Next: add demand, prices, and a live feed." |

## Part 2 — Tech-lead walkthrough (≈ 4:30)
| Time | Show | Say |
|---|---|---|
| 0:00–0:45 | README + folder tree | Purpose, stack (React/Vite/Recharts, FastAPI/pandas, Docker, Vercel), AI-tool disclosure. |
| 0:45–1:30 | Architecture sketch | Static CSV snapshot → pandas analysis → JSON API → React. Why a snapshot: Jan 2026 is fixed history; makes Vercel serverless fast and reliable. |
| 1:30–3:00 | `analysis.py` `decision_forecasts` | The core: per-target cut-off on D-1 in Europe/London (DST-safe), filter `publishTime <= cutoff`, take latest. Error sign convention. No-look-ahead band in `day_view`. |
| 3:00–3:40 | `tests/` | Show the 5 tests: cut-off, later-gate, sign, missing forecast, no leakage. |
| 3:40–4:10 | `fetch_data.py`, Dockerfile, vercel.json | Chunked downloads, param-name fallback; multi-stage Docker; Vercel rewrite to `api/index.py`. |
| 4:10–4:30 | Limitations | Assumed gate time, unconditional band, wind-only, static snapshot; next steps. |

Upload: YouTube → Visibility: **Unlisted**. Open the link in an incognito window to verify.
