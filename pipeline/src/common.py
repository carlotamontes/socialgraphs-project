"""Shared helpers: HTTP session, paths and the data log required by the project plan."""
import csv
import datetime as dt
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
LOG = ROOT / "data" / "data_log.csv"
for d in (RAW, PROC, RAW / "wikitext"):
    d.mkdir(parents=True, exist_ok=True)

UA = "SGI-WhoGetsRemembered/0.1 (DTU 02805 course project; python-requests)"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = UA

# Scope (Phase 0). Edit here, then re-run the pipeline.
BIRTH_MIN, BIRTH_MAX = 1920, 1980
FIELDS = {  # Wikidata occupation QID -> field label
    "Q169470": "physics",
    "Q593644": "chemistry",
    "Q864503": "biology",  # robustness field (Phase 5)
}
MAIN_FIELDS = {"physics", "chemistry"}


_last = {"t": 0.0}
MIN_INTERVAL = {"wikipedia.org": 1.0}  # seconds between requests (Wikimedia rate limits unauthenticated clients)


def _throttle(url):
    for host, gap in MIN_INTERVAL.items():
        if host in url:
            wait = _last["t"] + gap - time.time()
            if wait > 0:
                time.sleep(wait)
            _last["t"] = time.time()


def get(url, params=None, retries=5, pause=0.0, **kw):
    """GET with retry/backoff on 429/5xx."""
    for i in range(retries):
        _throttle(url)
        try:
            r = SESSION.get(url, params=params, timeout=120, **kw)
        except requests.RequestException:
            time.sleep(2 ** i)
            continue
        if r.status_code == 200:
            if pause:
                time.sleep(pause)
            return r
        if r.status_code in (429, 500, 502, 503, 504):
            wait = float(r.headers.get("Retry-After", 2 ** (i + 1)))
            time.sleep(min(wait, 60))
            continue
        r.raise_for_status()
    raise RuntimeError(f"Failed after {retries} tries: {url} {params}")


def log(source, query, n_records, note=""):
    """Append one line to data/data_log.csv (every query, its date, records returned)."""
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "source", "query", "n_records", "note"])
        w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    source, query, n_records, note])


def openalex_params(extra=None):
    p = dict(extra or {})
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        p["api_key"] = key
    return p
