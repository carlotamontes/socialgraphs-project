"""Step 1 - Wikidata: who is in the dataset.

Gets every human whose occupation (P106) is one of the chosen fields, born in
[min_year, max_year], with an English Wikipedia page. For each: gender (P21),
birth year (P569), ORCID (P496) and OpenAlex ID (P10283) when present.

Output: data/wikidata_scientists.csv  (one row per person)
        data/raw/wikidata_<field>.json (raw SPARQL answers)

Usage:
    python src/01_wikidata.py                         # physicists + chemists, 1920-1980
    python src/01_wikidata.py --fields physicist chemist biologist
    python src/01_wikidata.py --min-year 1930 --max-year 1975
    python src/01_wikidata.py --subclasses            # also 'theoretical physicist' etc.
"""
from __future__ import annotations

import argparse
import json
from urllib.parse import unquote

import pandas as pd

from common import DATA, RAW, log_query, make_session, request_json

SPARQL_URL = "https://query.wikidata.org/sparql"

FIELDS = {                      # occupation QIDs
    "physicist": "Q169470",
    "chemist": "Q593644",
    "biologist": "Q864503",
}

GENDER = {
    "Q6581097": "male",
    "Q6581072": "female",
    "Q1052281": "trans woman",
    "Q2449503": "trans man",
    "Q48270": "non-binary",
}


def build_query(occ_qid: str, min_year: int, max_year: int, subclasses: bool) -> str:
    occ = (f"?person wdt:P106 ?occ . ?occ wdt:P279* wd:{occ_qid} ."
           if subclasses else f"?person wdt:P106 wd:{occ_qid} .")
    return f"""
SELECT ?person ?article ?gender ?birth ?orcid ?openalex WHERE {{
  {occ}
  ?person wdt:P31 wd:Q5 ;
          wdt:P569 ?birth .
  FILTER(?birth >= "{min_year}-01-01T00:00:00Z"^^xsd:dateTime &&
         ?birth <  "{max_year + 1}-01-01T00:00:00Z"^^xsd:dateTime)
  ?article schema:about ?person ;
           schema:isPartOf <https://en.wikipedia.org/> .
  OPTIONAL {{ ?person wdt:P21 ?gender . }}
  OPTIONAL {{ ?person wdt:P496 ?orcid . }}
  OPTIONAL {{ ?person wdt:P10283 ?openalex . }}
}}"""


def run_query(session, query: str) -> list[dict]:
    res = request_json(session, SPARQL_URL, data={"query": query, "format": "json"},
                       method="POST", timeout=120,
                       headers={"Accept": "application/sparql-results+json"})
    return res["results"]["bindings"]


def qid_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def title_of(article_url: str) -> str:
    return unquote(article_url.split("/wiki/", 1)[1]).replace("_", " ")


def year_of(value: str) -> int | None:
    """'1955-03-12T00:00:00Z' -> 1955."""
    value = value.lstrip("+")
    try:
        return int(value[:4])
    except ValueError:
        return None


def bindings_to_rows(bindings: list[dict], field: str) -> list[dict]:
    rows = []
    for b in bindings:
        g = b.get("gender", {}).get("value")
        rows.append({
            "qid": qid_of(b["person"]["value"]),
            "title": title_of(b["article"]["value"]),
            "gender_qid": qid_of(g) if g else None,
            "birth_year": year_of(b.get("birth", {}).get("value", "")),
            "orcid": b.get("orcid", {}).get("value"),
            "openalex_id": b.get("openalex", {}).get("value"),
            "field": field,
        })
    return rows


def _join_unique(s: pd.Series) -> str | None:
    vals = sorted({v for v in s.dropna().astype(str) if v})
    return ";".join(vals) if vals else None


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """One row per person. Multiple values (e.g. two birth dates, two ORCIDs,
    physicist AND chemist) come back as several SPARQL rows."""
    def gender_label(s: pd.Series) -> str:
        vals = {GENDER.get(v, v) for v in s.dropna()}
        if not vals:
            return "missing"
        return vals.pop() if len(vals) == 1 else "multiple"

    out = df.groupby("qid").agg(
        title=("title", "first"),
        gender=("gender_qid", gender_label),
        birth_year=("birth_year", "min"),
        birth_year_max=("birth_year", "max"),
        fields=("field", _join_unique),
        orcid=("orcid", _join_unique),
        openalex_id=("openalex_id", _join_unique),
    ).reset_index()
    out["birth_year_conflict"] = (out["birth_year_max"] - out["birth_year"]) > 1
    out = out.drop(columns="birth_year_max")
    out["birth_year"] = out["birth_year"].astype("Int64")
    return out.sort_values("qid").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields", nargs="+", default=["physicist", "chemist"],
                    choices=list(FIELDS))
    ap.add_argument("--min-year", type=int, default=1920)
    ap.add_argument("--max-year", type=int, default=1980)
    ap.add_argument("--subclasses", action="store_true",
                    help="include sub-occupations (slower, much larger)")
    args = ap.parse_args()

    session = make_session()
    rows = []
    for field in args.fields:
        q = build_query(FIELDS[field], args.min_year, args.max_year, args.subclasses)
        print(f"Querying Wikidata for {field}s born {args.min_year}-{args.max_year} ...")
        bindings = run_query(session, q)
        (RAW / f"wikidata_{field}.json").write_text(
            json.dumps({"query": q, "bindings": bindings}, ensure_ascii=False),
            encoding="utf-8")
        field_rows = bindings_to_rows(bindings, field)
        n_people = len({r["qid"] for r in field_rows})
        print(f"  {len(bindings)} rows -> {n_people} people")
        log_query("Wikidata SPARQL",
                  f"P106={FIELDS[field]} ({field}), born {args.min_year}-{args.max_year}, "
                  f"has enwiki, subclasses={args.subclasses}",
                  n_people, f"{len(bindings)} raw rows")
        rows += field_rows

    df = aggregate(pd.DataFrame(rows))
    out = DATA / "wikidata_scientists.csv"
    df.to_csv(out, index=False, encoding="utf-8")

    print(f"\nSaved {len(df)} people to {out}")
    print("\nBy field (people can be in several):")
    print(df["fields"].value_counts().to_string())
    print("\nBy gender:")
    print(df["gender"].value_counts(dropna=False).to_string())
    print(f"\nWith ORCID:       {df['orcid'].notna().mean():.1%}")
    print(f"With OpenAlex ID: {df['openalex_id'].notna().mean():.1%}")
    print(f"With either:      {(df['orcid'].notna() | df['openalex_id'].notna()).mean():.1%}")
    women = df[df.gender == "female"]
    print(f"Women with an ID: {(women['orcid'].notna() | women['openalex_id'].notna()).sum()}"
          f" of {len(women)}  (M1 needs >= 100 women matched)")


if __name__ == "__main__":
    main()
