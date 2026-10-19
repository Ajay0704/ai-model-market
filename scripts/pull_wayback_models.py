"""Pull monthly Internet Archive snapshots of OpenRouter's public model list (prices over time).

The live /api/v1/models list only has today's prices and drops retired models. The Wayback Machine
captured the same endpoint about once a month from January 2025, so those captures give a price
history and prices for retired models.

Usage: python scripts/pull_wayback_models.py [--force]
Saves data/raw/models_wayback/<timestamp>.json as {"request": {...}, "response": <the archived JSON>}.
Stops at the first capture that is not valid model-list JSON.
"""

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "models_wayback"
CDX = "https://web.archive.org/cdx/search/cdx"
TARGET = "openrouter.ai/api/v1/models"


def get_with_backoff(url, waits=(30, 90, 180)):
    """The Archive refuses connections when hit too fast; wait and retry only on connection errors."""
    for w in (*waits, None):
        try:
            return requests.get(url, timeout=120)
        except requests.exceptions.ConnectionError:
            if w is None:
                raise
            print(f"  connection refused, waiting {w}s")
            time.sleep(w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    q = {"url": TARGET, "from": "2025", "output": "json", "fl": "timestamp,statuscode",
         "filter": "statuscode:200", "collapse": "timestamp:6"}  # first capture of each month
    caps = requests.get(CDX, params=q, timeout=60).json()[1:]
    print(f"{len(caps)} monthly captures")
    for i, (ts, _) in enumerate(caps, 1):
        path = OUT / f"{ts}.json"
        if path.exists() and not a.force:
            print(f"skip {path.name}")
            continue
        url = f"https://web.archive.org/web/{ts}id_/https://{TARGET}"  # id_ = the raw archived bytes
        r = get_with_backoff(url)
        try:
            body = r.json()
            assert r.status_code == 200 and isinstance(body.get("data"), list) and body["data"]
        except Exception:
            sys.exit(f"STOP at {ts}: status {r.status_code}, not a model list: {r.text[:200]}")
        record = {"request": {"url": url, "capture_timestamp": ts,
                              "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
                  "response": body}
        path.write_text(json.dumps(record))
        print(f"[{i}/{len(caps)}] {ts}: {len(body['data'])} models")
        time.sleep(6)


if __name__ == "__main__":
    main()
