"""Step 3 - OpenAlex: scientific impact.

For every page in data/nodes.csv (run step 2 first):
  * if Wikidata gave an OpenAlex ID  -> GET /authors/<id>
  * else if Wikidata gave an ORCID   -> GET /authors/orcid:<orcid>
  (single-record lookups are free with an API key)
  * first publication year: one /works list call per matched author (cheap, can be
    switched off with --no-first-year)
  * people with no ID: a name search saves the top 5 candidates to
    data/raw/openalex_name_candidates.jsonl - NOT used in impact.csv; choosing
    among them is Phase 2 (matching), with a hand-checked sample.

Needs a free API key (openalex.org -> Settings -> API) in project/.env:
    OPENALEX_API_KEY=xxxx

Output: data/impact.csv, cached answers in data/raw/openalex/<qid>.json

Usage:
    python src/03_openalex.py --limit 50
    python src/03_openalex.py
    python src/03_openalex.py --no-name-search --no-first-year
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import time
import unicodedata

import pandas as pd

from common import (DATA, OPENALEX_API_KEY, RAW, log_query, make_session,
                    request_json)

BASE = "https://api.openalex.org"
CACHE = RAW / "openalex"
CACHE.mkdir(parents=True, exist_ok=True)
CANDIDATES = RAW / "openalex_name_candidates.jsonl"
PAUSE = 0.12          # ~8 requests/s, well under the 100/s cap


def params(**kw):
    p = dict(kw)
    if OPENALEX_API_KEY:
        p["api_key"] = OPENALEX_API_KEY
    return p


def clean_orcid(o: str) -> str:
    return o.strip().rsplit("/", 1)[-1]


def clean_oa_id(a: str) -> str:
    return a.strip().rsplit("/", 1)[-1].upper()


def plain_name(title: str) -> str:
    """'Chen Ning Yang (physicist)' -> 'Chen Ning Yang'"""
    return re.sub(r"\s*\(.*?\)\s*$", "", title).strip()


def name_similarity(a: str, b: str) -> float:
    def norm(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z ]", "", s.lower())
    return round(difflib.SequenceMatcher(None, norm(a), norm(b)).ratio(), 3)


def get_author(session, key: str) -> dict | None:
    """key = 'A123...' or 'orcid:0000-...'"""
    res = request_json(session, f"{BASE}/authors/{key}", params=params())
    time.sleep(PAUSE)
    return res


def first_pub_year(session, author_id: str) -> int | None:
    res = request_json(session, f"{BASE}/works", params=params(
        filter=f"author.id:{author_id}", sort="publication_year:asc",
        per_page=1, select="publication_year"))
    time.sleep(PAUSE)
    try:
        return res["results"][0]["publication_year"]
    except (TypeError, KeyError, IndexError):
        return None


def summarise(a: dict) -> dict:
    topics = a.get("topics") or []
    inst = a.get("last_known_institutions") or []
    stats = a.get("summary_stats") or {}
    return {
        "openalex_id": clean_oa_id(a["id"]),
        "oa_display_name": a.get("display_name"),
        "oa_orcid": clean_orcid(a["orcid"]) if a.get("orcid") else None,
        "works_count": a.get("works_count"),
        "cited_by_count": a.get("cited_by_count"),
        "h_index": stats.get("h_index"),
        "i10_index": stats.get("i10_index"),
        "top_topic": topics[0]["display_name"] if topics else None,
        "top_field": (topics[0].get("field") or {}).get("display_name") if topics else None,
        "last_institution": inst[0].get("display_name") if inst else None,
    }


def lookup_person(session, row) -> dict:
    """All ID-based lookups for one person -> one cached dict."""
    oa_ids = [clean_oa_id(x) for x in str(row.openalex_id).split(";")] \
        if isinstance(row.openalex_id, str) else []
    orcids = [clean_orcid(x) for x in str(row.orcid).split(";")] \
        if isinstance(row.orcid, str) else []
    found = {}
    for a in oa_ids:
        rec = get_author(session, a)
        if rec:
            found[clean_oa_id(rec["id"])] = {"via": "openalex_id", "record": rec}
    for o in orcids:
        rec = get_author(session, f"orcid:{o}")
        if rec:
            aid = clean_oa_id(rec["id"])
            if aid in found:
                found[aid]["via"] = "openalex_id+orcid"
            else:
                found[aid] = {"via": "orcid", "record": rec}
    return {"qid": row.qid, "n_wikidata_oa_ids": len(oa_ids),
            "n_wikidata_orcids": len(orcids), "found": found}


def name_candidates(session, row) -> dict:
    res = request_json(session, f"{BASE}/authors", params=params(
        search=plain_name(row.wiki_title), per_page=5,
        select="id,display_name,orcid,works_count,cited_by_count,"
               "last_known_institutions,topics,summary_stats"))
    time.sleep(PAUSE)
    return {"qid": row.qid, "wiki_title": row.wiki_title,
            "candidates": [summarise(c) for c in (res or {}).get("results", [])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-first-year", action="store_true")
    ap.add_argument("--no-name-search", action="store_true")
    args = ap.parse_args()

    if not OPENALEX_API_KEY:
        print("WARNING: no OPENALEX_API_KEY in project/.env - OpenAlex only allows a "
              "tiny daily budget without one. Get a free key at openalex.org/settings/api")

    nodes = pd.read_csv(DATA / "nodes.csv", dtype=str)
    if args.limit:
        nodes = nodes.head(args.limit)
    session = make_session()

    has_id = nodes.orcid.notna() | nodes.openalex_id.notna()
    print(f"{has_id.sum()} of {len(nodes)} people have an ORCID or OpenAlex ID on Wikidata")

    rows = []
    n_req = 0
    for i, row in enumerate(nodes[has_id].itertuples(), 1):
        cache = CACHE / f"{row.qid}.json"
        if cache.exists() and not args.refresh:
            res = json.loads(cache.read_text(encoding="utf-8"))
        else:
            res = lookup_person(session, row)
            n_req += 1
            if not args.no_first_year:
                for aid, f in res["found"].items():
                    f["first_pub_year"] = first_pub_year(session, aid)
            cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        print(f"  {i}/{has_id.sum()}", end="\r")

        found = res["found"]
        if not found:
            rows.append({"qid": row.qid, "match_method": "id_not_found"})
            continue
        # OpenAlex sometimes splits one person into several author profiles:
        # keep the largest (most works) and record how many there were.
        best_id, best = max(found.items(),
                            key=lambda kv: kv[1]["record"].get("works_count") or 0)
        out = {"qid": row.qid, "match_method": best["via"],
               "n_openalex_profiles": len(found),
               "first_pub_year": best.get("first_pub_year"),
               **summarise(best["record"])}
        out["name_similarity"] = name_similarity(plain_name(row.wiki_title),
                                                 out["oa_display_name"])
        rows.append(out)
    print()
    log_query("OpenAlex API", "authors by Wikidata OpenAlex ID / ORCID (+ first work year)",
              sum(1 for r in rows if r["match_method"] != "id_not_found"),
              f"{n_req} people looked up this run")

    # people without an ID -> candidates for Phase 2
    if not args.no_name_search:
        done = set()
        if CANDIDATES.exists():
            done = {json.loads(l)["qid"] for l in CANDIDATES.open(encoding="utf-8")}
        todo = nodes[~has_id & ~nodes.qid.isin(done)]
        print(f"Name search for {len(todo)} people without an ID ...")
        with CANDIDATES.open("a", encoding="utf-8") as f:
            for i, row in enumerate(todo.itertuples(), 1):
                f.write(json.dumps(name_candidates(session, row), ensure_ascii=False) + "\n")
                print(f"  {i}/{len(todo)}", end="\r")
        print()
        log_query("OpenAlex API", "author name search (top 5 candidates) for people without IDs",
                  len(todo), "candidates only; matching happens in Phase 2")

    impact = pd.DataFrame(rows)
    impact.to_csv(DATA / "impact.csv", index=False, encoding="utf-8")

    matched = impact[impact.match_method != "id_not_found"]
    g = nodes.set_index("qid").gender
    print(f"\nimpact.csv: {len(matched)} people matched by ID")
    print(matched.qid.map(g).value_counts().to_string())
    n_women = (matched.qid.map(g) == "female").sum()
    print(f"\nM1 check - women matched: {n_women} (need >= 100)")
    low = matched[matched.name_similarity < 0.6]
    if len(low):
        print(f"{len(low)} matches have a low name similarity (<0.6) - check them by hand in Phase 2")


if __name__ == "__main__":
    main()
