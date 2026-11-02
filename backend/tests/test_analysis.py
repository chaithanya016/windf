import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app import analysis as an  # noqa: E402


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def frames():
    # Target: 2026-01-10 12:00Z. Cut-off 09:00 on 9 Jan. Three runs: before, just after, much later.
    f = pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00")] * 3,
        "publishTime": [ts("2026-01-09 08:00"), ts("2026-01-09 09:30"), ts("2026-01-10 06:00")],
        "forecast": [1000.0, 1500.0, 1900.0],
    })
    a = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "actual": [1800.0]})
    return a, f


def test_picks_latest_forecast_before_cutoff():
    a, f = frames()
    df = an.decision_forecasts(a, f, "09:00")
    assert len(df) == 1 and df.forecast.iloc[0] == 1000.0  # 09:30 and next-day runs are unusable


def test_later_cutoff_uses_newer_run():
    a, f = frames()
    df = an.decision_forecasts(a, f, "10:00")
    assert df.forecast.iloc[0] == 1500.0


def test_error_sign_and_metrics():
    a, f = frames()
    df = an.decision_forecasts(a, f, "09:00")
    assert df.error.iloc[0] == -800.0  # under-forecast
    s = an.summarize(df)
    assert s["mae"] == 800.0 and s["bias"] == -800.0 and s["n"] == 1


def test_no_forecast_before_cutoff_drops_period():
    a, f = frames()
    f = f.iloc[1:]
    assert an.decision_forecasts(a, f, "09:00").empty


def test_band_uses_only_past_days():
    rows = []
    for d in range(1, 6):
        for h in range(48):
            t = ts(f"2026-01-0{d} 00:00") + pd.Timedelta(minutes=30 * h)
            rows.append((t, ts(f"2026-01-0{d-1 if d>1 else 1} 08:00") - pd.Timedelta(days=1), 100.0, 90.0 if d < 5 else 0.0))
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast", "actual"])
    df = an._add_errors(df)
    v = an.day_view(df, "2026-01-05")
    assert v["band"]["history_days"] == 4 and v["band"]["q05"] == 10.0  # day 5 errors excluded
    assert an.day_view(df, "2026-01-01")["band"] is None
