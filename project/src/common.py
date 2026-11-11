"""Shared helpers: paths, HTTP with retries, and the data log.

Every script imports this. Settings live in project/.env (see .env.example).
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]          # .../project
DATA = ROOT / "data"
RAW = DATA / "raw"
TEXT = DATA / "text"
for _p in (DATA, RAW, TEXT):
    _p.mkdir(parents=True, exist_ok=True)

LOG_FILE = DATA / "data_log.csv"


def _load_env() -> None:
    """Minimal .env reader (KEY=value per line) so we don't need python-dotenv."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "").strip()
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()

# Wikimedia asks every client to identify itself with a contact address.
USER_AGENT = (
    "WhoGetsRemembered/0.1 (DTU 02805 student project; "
    f"{CONTACT_EMAIL or 'contact not set'}) python-requests"
)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def request_json(session, url, params=None, data=None, method="GET",
                 max_tries=6, timeout=90, headers=None):
    """GET/POST returning parsed JSON. Retries on network errors, 429 and 5xx
    with exponential back-off. Returns None on 404."""
    for attempt in range(max_tries):
        try:
            r = session.request(method, url, params=params, data=data,
                                timeout=timeout, headers=headers)
        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  network error ({e.__class__.__name__}), retry in {wait}s")
            time.sleep(wait)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        if r.status_code in (429, 500, 502, 503, 504):
            try:
                wait = int(r.headers.get("Retry-After", ""))
            except ValueError:
                wait = 2 ** attempt
            wait = max(wait, 2 ** attempt)
            print(f"  HTTP {r.status_code}, retry in {wait}s")
            time.sleep(wait)
            continue
        # 400/401/403 etc.: something is wrong with the request itself
        raise RuntimeError(f"HTTP {r.status_code} for {r.url}\n{r.text[:500]}")
    raise RuntimeError(f"Gave up after {max_tries} tries: {url}")


def log_query(source: str, description: str, n_records: int, notes: str = "") -> None:
    """Append one line to data/data_log.csv (date, source, what, how many)."""
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "source", "description", "n_records", "notes"])
        w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    source, description, n_records, notes])


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]
