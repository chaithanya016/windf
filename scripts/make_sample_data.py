"""SYNTHETIC data in the same schema as the real snapshot, for offline dev/tests only.
Creates backend/data/SAMPLE_DATA so the UI shows a 'sample data' banner.
Replace with real data via scripts/fetch_data.py.
"""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "backend" / "data"
UTC = timezone.utc
rng = np.random.default_rng(42)
start, end = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
t0 = start - timedelta(days=4)
slots = [t0 + timedelta(minutes=30 * i) for i in range(int((end - t0).total_seconds() // 1800))]

# smooth AR(1)-ish "true" wind, MW, UK capacity ~ 15-20 GW
x, level = [], 8000.0
for _ in slots:
    level += 0.02 * (8000 - level) + rng.normal(0, 180)
    x.append(min(max(level, 300), 17000))
truth = dict(zip(slots, x))

iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "actuals.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["startTime", "generation"])
    for s in slots:
        if start <= s < end:
            w.writerow([iso(s), round(truth[s])])

with open(OUT / "forecasts.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["startTime", "publishTime", "generation"])
    pub = t0
    while pub < end:                      # a new forecast run every 3 hours
        for h in range(1, 49 * 2):        # up to ~48h ahead
            s = pub + timedelta(minutes=30 * h)
            if s in truth and start <= s < end:
                sigma = 150 + 55 * (h / 2)  # error grows with lead time
                w.writerow([iso(s), iso(pub), round(max(0, truth[s] + rng.normal(0, sigma)))])
        pub += timedelta(hours=3)
(OUT / "SAMPLE_DATA").write_text("synthetic")
print("sample data written")
