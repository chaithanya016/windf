"""Pure analysis functions (no I/O) so they are easy to unit test.

Key idea: a buyer commits in the day-ahead auction on D-1 at a gate time (default
09:00 UK). The only forecast they could have used for a target period on day D is
the LATEST one with publishTime <= that cut-off. Accuracy is measured on exactly
that "decision forecast", not on whichever forecast happens to be newest.
"""
import numpy as np
import pandas as pd

TZ = "Europe/London"
MIN_HISTORY_ROWS = 48  # one day of half-hours before we trust an error band


def decision_forecasts(actuals: pd.DataFrame, forecasts: pd.DataFrame, cutoff: str = "09:00") -> pd.DataFrame:
    """For each target half-hour, the latest forecast published before the D-1 cut-off."""
    hh, mm = (int(x) for x in cutoff.split(":"))
    f = forecasts.copy()
    local_wall = f["startTime"].dt.tz_convert(TZ).dt.tz_localize(None)
    cut_local = local_wall.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=hh, minutes=mm)
    f["cutoff"] = cut_local.dt.tz_localize(TZ, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    f = f.dropna(subset=["cutoff"])
    f = f[f["publishTime"] <= f["cutoff"]]
    f = f.sort_values("publishTime").groupby("startTime", as_index=False).last()
    df = f.merge(actuals, on="startTime", how="inner")
    return _add_errors(df)


def _add_errors(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["error"] = df["forecast"] - df["actual"]  # +ve = over-forecast (bought too little thermal)
    df["abs_error"] = df["error"].abs()
    df["lead_hours"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    df["local_date"] = df["startTime"].dt.tz_convert(TZ).dt.strftime("%Y-%m-%d")
    df["local_hour"] = df["startTime"].dt.tz_convert(TZ).dt.hour
    return df


def _f(x, nd=1):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    e, a = df["error"], df["abs_error"]
    total_actual = df["actual"].sum()
    return {
        "n": int(len(df)),
        "mae": _f(a.mean()),
        "rmse": _f(np.sqrt((e**2).mean())),
        "bias": _f(e.mean()),
        "wmape": _f(a.sum() / total_actual * 100) if total_actual > 0 else None,
        "p90_abs": _f(a.quantile(0.90)),
        "p95_abs": _f(a.quantile(0.95)),
        "max_abs": _f(a.max()),
        "err_q05": _f(e.quantile(0.05)),
        "err_q50": _f(e.quantile(0.50)),
        "err_q95": _f(e.quantile(0.95)),
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    g = df.groupby("local_hour").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size"))
    return [{"hour": int(h), "mae": _f(r.mae), "bias": _f(r.bias), "n": int(r.n)} for h, r in g.iterrows()]


def by_day(df: pd.DataFrame) -> list[dict]:
    g = df.groupby("local_date").agg(
        mae=("abs_error", "mean"), bias=("error", "mean"),
        mean_actual=("actual", "mean"), mean_forecast=("forecast", "mean"),
    )
    return [{"date": d, **{k: _f(v) for k, v in r.items()}} for d, r in g.iterrows()]


def error_histogram(df: pd.DataFrame, bins: int = 24) -> list[dict]:
    if df.empty:
        return []
    counts, edges = np.histogram(df["error"], bins=bins)
    return [{"from": _f(edges[i], 0), "to": _f(edges[i + 1], 0), "count": int(c)} for i, c in enumerate(counts)]


def by_lead(actuals: pd.DataFrame, forecasts: pd.DataFrame, bucket: int = 6, max_lead: int = 60) -> list[dict]:
    """Error vs lead time using ALL published forecasts (shows value of waiting for newer runs)."""
    df = _add_errors(forecasts.merge(actuals, on="startTime", how="inner"))
    df = df[(df.lead_hours >= 0) & (df.lead_hours < max_lead)]
    df["bucket"] = (df.lead_hours // bucket * bucket).astype(int)
    g = df.groupby("bucket").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size"))
    return [{"lead_from": int(b), "lead_to": int(b) + bucket, "mae": _f(r.mae), "bias": _f(r.bias), "n": int(r.n)}
            for b, r in g.iterrows()]


def day_view(decision: pd.DataFrame, date: str) -> dict:
    """Forecast a buyer would see for delivery day `date`, with an empirical error band
    learned ONLY from earlier days (no look-ahead)."""
    day = decision[decision.local_date == date].sort_values("startTime")
    hist = decision[decision.local_date < date]
    band = None
    if len(hist) >= MIN_HISTORY_ROWS:
        q05, q95 = hist["error"].quantile(0.05), hist["error"].quantile(0.95)
        band = {"q05": _f(q05), "q95": _f(q95), "history_days": int(hist.local_date.nunique())}
    rows = []
    for r in day.itertuples():
        row = {"startTime": r.startTime.isoformat(), "forecast": _f(r.forecast), "actual": _f(r.actual),
               "error": _f(r.error), "publishTime": r.publishTime.isoformat()}
        if band:  # actual plausibly lies in [forecast - q95, forecast - q05]
            row["lower"] = _f(max(0.0, r.forecast - band["q95"]))
            row["upper"] = _f(r.forecast - band["q05"])
        rows.append(row)
    summary = {}
    if not day.empty:
        summary = {
            "periods": int(len(day)),
            "forecast_mwh": _f(day.forecast.sum() * 0.5, 0),
            "actual_mwh": _f(day.actual.sum() * 0.5, 0),
            "peak_forecast_mw": _f(day.forecast.max(), 0),
            "min_forecast_mw": _f(day.forecast.min(), 0),
            "latest_publish_used": day.publishTime.max().isoformat(),
            "earliest_publish_used": day.publishTime.min().isoformat(),
            "mae": _f(day.abs_error.mean()),
        }
    return {"date": date, "band": band, "summary": summary, "rows": rows}
