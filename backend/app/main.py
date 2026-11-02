import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import analysis as an
from .data import PERIOD_END, PERIOD_START, load_actuals, load_forecasts

app = FastAPI(title="Wind Forecast Pilot API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

DEFAULT_CUTOFF = "09:00"
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _decision(cutoff: str):
    if not _TIME.match(cutoff):
        raise HTTPException(400, "cutoff must be HH:MM (UK local time)")
    try:
        return an.decision_forecasts(load_actuals(), load_forecasts(), cutoff)
    except FileNotFoundError:
        raise HTTPException(503, "Data snapshot missing. Run scripts/fetch_data.py (or make_sample_data.py).")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "period_start": PERIOD_START.date().isoformat(),
        "period_end_exclusive": PERIOD_END.date().isoformat(),
        "default_cutoff": DEFAULT_CUTOFF,
        "timezone": an.TZ,
        "sample_data": os.path.exists(Path(__file__).resolve().parent.parent / "data" / "SAMPLE_DATA"),
    }


@app.get("/api/day")
def day(date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"), cutoff: str = DEFAULT_CUTOFF):
    """Forecast available at the D-1 cut-off for delivery day `date`, plus actuals and error band."""
    df = _decision(cutoff)
    out = an.day_view(df, date)
    if not out["rows"]:
        raise HTTPException(404, f"No data for {date}")
    return out


@app.get("/api/accuracy")
def accuracy(cutoff: str = DEFAULT_CUTOFF):
    df = _decision(cutoff)
    return {
        "cutoff": cutoff,
        "summary": an.summarize(df),
        "by_hour": an.by_hour(df),
        "by_day": an.by_day(df),
        "histogram": an.error_histogram(df),
    }


@app.get("/api/lead-time")
def lead_time():
    return {"buckets": an.by_lead(load_actuals(), load_forecasts())}


static_dir = os.getenv("STATIC_DIR")
if static_dir and Path(static_dir).exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
