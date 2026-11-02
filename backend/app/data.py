"""Data loading. Reads the January-2026 snapshot produced by scripts/fetch_data.py."""
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
PERIOD_START = pd.Timestamp("2026-01-01", tz="UTC")  # target (delivery) window
PERIOD_END = pd.Timestamp("2026-02-01", tz="UTC")


@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "actuals.csv")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.rename(columns={"generation": "actual"}).dropna()
    df = df[(df.startTime >= PERIOD_START) & (df.startTime < PERIOD_END)]
    return df.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "forecasts.csv")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.rename(columns={"generation": "forecast"}).dropna()
    df = df[(df.startTime >= PERIOD_START) & (df.startTime < PERIOD_END)]
    return df.drop_duplicates(["startTime", "publishTime"]).reset_index(drop=True)
