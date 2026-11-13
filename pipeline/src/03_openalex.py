"""Phase 1c: scientific impact from OpenAlex, matched by identifiers stored in Wikidata.

Matching order (as in the plan): OpenAlex ID from Wikidata (P10283), then ORCID (P496).
Name-based matching is deliberately not used here (ambiguity + API budget); see docs/scope_note.md.

Output: data/processed/impact.csv
"""
import difflib
import json
import unicodedata

import pandas as pd
from tqdm import tqdm

from common import PROC, RAW, get, log, openalex_params

API = "https://api.openalex.org/authors"
CACHE = RAW / "openalex_authors.jsonl"
SELECT = "id,orcid,display_name,display_name_alternatives,works_count,cited_by_count,summary_stats,topics"


def chunks(xs, n=50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def fetch(filter_key, values):
    out = []
    for batch in tqdm(list(chunks(values)), desc=filter_key):
        r = get(API, params=openalex_params({"filter": f"{filter_key}:" + "|".join(batch),
                                             "per-page": 200, "select": SELECT}), pause=0.1)
        out += r.json()["results"]
    log("OpenAlex API", f"/authors filter={filter_key} for {len(values)} ids", len(out))
    return out


def simplify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(w for w in s.replace(".", " ").replace("-", " ").split() if len(w) > 1)


def name_sim(a, names):
    a = simplify(a)
    return max((difflib.SequenceMatcher(None, a, simplify(n)).ratio() for n in names if n), default=0)


def run():
    people = pd.read_csv(PROC / "scientists_wikidata.csv")
    # Wikidata P10283 holds some non-author IDs (concepts, publishers) and lowercase variants.
    people["oa_clean"] = (people.openalex_wd.str.rsplit("/", n=1).str[-1].str.upper()
                          .where(lambda s: s.str.fullmatch(r"A\d+", na=False)))
    if CACHE.exists():
        authors = [json.loads(l) for l in CACHE.open()]
    else:
        oa_ids = sorted(set(people.oa_clean.dropna()))
        orcids = sorted(set(people.orcid.dropna()))
        authors = fetch("openalex", oa_ids) + fetch("orcid", orcids)
        with CACHE.open("w") as f:
            for a in authors:
                f.write(json.dumps(a) + "\n")

    by_oa = {a["id"].rsplit("/", 1)[-1]: a for a in authors}
    by_orcid = {}
    for a in authors:
        if a.get("orcid"):
            by_orcid.setdefault(a["orcid"].rsplit("/", 1)[-1], []).append(a)

    rows = []
    for p in people.itertuples():
        cand, method = [], None
        if isinstance(p.oa_clean, str) and p.oa_clean in by_oa:
            cand, method = [by_oa[p.oa_clean]], "openalex_id"
        elif isinstance(p.orcid, str) and p.orcid in by_orcid:
            cand, method = by_orcid[p.orcid], "orcid"
        if not cand:
            continue
        # Several OpenAlex profiles can share an ORCID (split profiles): sum them, flag it.
        best = max(cand, key=lambda a: a["works_count"])
        names = [best["display_name"]] + (best.get("display_name_alternatives") or [])
        topics = best.get("topics") or []
        rows.append({
            "qid": p.qid, "openalex_id": best["id"].rsplit("/", 1)[-1], "match_method": method,
            "n_profiles": len(cand),
            "citations": sum(a["cited_by_count"] for a in cand),
            "works": sum(a["works_count"] for a in cand),
            "h_index": (best.get("summary_stats") or {}).get("h_index"),
            "oa_name": best["display_name"],
            "name_similarity": round(name_sim(p.label or p.title, names), 3),
            "top_field": topics[0]["field"]["display_name"] if topics else None,
            "top_subfield": topics[0]["subfield"]["display_name"] if topics else None,
        })
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "impact.csv", index=False)
    log("derived", "impact.csv: people matched to OpenAlex by ID", len(df))
    m = people.merge(df, on="qid")
    print(m.groupby("gender").size())
    print("low name similarity (<0.6):", (df.name_similarity < 0.6).sum(),
          "| multi-profile ORCIDs:", (df.n_profiles > 1).sum())


if __name__ == "__main__":
    run()
