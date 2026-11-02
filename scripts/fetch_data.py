"""Download January-2026 wind actuals (FUELHH) and forecasts (WINDFOR) from Elexon BMRS
into backend/data/*.csv. Standard library only. Run once, commit the CSVs.

    python scripts/fetch_data.py

Elexon has renamed query parameters between API revisions, so each endpoint tries a list
of known parameter-name pairs and uses the first that the server accepts.
"""
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = Path(__file__).resolve().parent.parent / "backend" / "data"
UTC = timezone.utc

# Targets: Jan 2026. Forecasts for early-Jan targets are published from late Dec.
TARGET_START, TARGET_END = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
PUBLISH_START = TARGET_START - timedelta(days=4)


def get(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.load(r)
    return body["data"] if isinstance(body, dict) and "data" in body else body


def fetch_window(dataset, param_pairs, start, end, extra=None):
    last_err = None
    for p_from, p_to, fmt in param_pairs:
        q = {p_from: start.strftime(fmt), p_to: end.strftime(fmt), **(extra or {})}
        url = f"{BASE}/{dataset}/stream?{urllib.parse.urlencode(q)}"
        try:
            return get(url)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code != 400:
                raise
    raise RuntimeError(f"{dataset}: no parameter set accepted ({last_err})")


def chunks(start, end, days):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    iso = "%Y-%m-%dT%H:%MZ"
    # Actuals (FUELHH, WIND only)
    actuals = {}
    for s, e in chunks(TARGET_START, TARGET_END, 7):
        rows = fetch_window("FUELHH", [("settlementDateFrom", "settlementDateTo", "%Y-%m-%d"),
                                       ("from", "to", iso)], s, e, {"fuelType": "WIND"})
        for r in rows:
            if r.get("fuelType") == "WIND":
                actuals[r["startTime"]] = r["generation"]
        print(f"FUELHH {s:%F}..{e:%F}: {len(actuals)} rows so far")
    with open(OUT / "actuals.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["startTime", "generation"])
        w.writerows(sorted(actuals.items()))

    # Forecasts (WINDFOR)
    fc = {}
    for s, e in chunks(PUBLISH_START, TARGET_END, 3):
        rows = fetch_window("WINDFOR", [("publishDateTimeFrom", "publishDateTimeTo", iso),
                                        ("from", "to", iso)], s, e)
        for r in rows:
            fc[(r["startTime"], r["publishTime"])] = r["generation"]
        print(f"WINDFOR {s:%F}..{e:%F}: {len(fc)} rows so far")
    with open(OUT / "forecasts.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["startTime", "publishTime", "generation"])
        w.writerows((k[0], k[1], v) for k, v in sorted(fc.items()))
    sample_flag = OUT / "SAMPLE_DATA"
    if sample_flag.exists():
        sample_flag.unlink()
    print("Done. Commit backend/data/*.csv")


if __name__ == "__main__":
    sys.exit(main())
