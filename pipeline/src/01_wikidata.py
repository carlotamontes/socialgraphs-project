"""Phase 1a: scientist list from Wikidata (gender, field, birth year, identifiers).

Output: data/processed/scientists_wikidata.csv (one row per person).
"""
import pandas as pd

from common import BIRTH_MAX, BIRTH_MIN, FIELDS, PROC, get, log

ENDPOINT = "https://query.wikidata.org/sparql"

TEMPLATE = """
SELECT ?p ?title ?birth
       (GROUP_CONCAT(DISTINCT ?g; separator="|") AS ?genders)
       (SAMPLE(?orcid_) AS ?orcid) (SAMPLE(?oa_) AS ?openalex)
       (SAMPLE(?label_) AS ?label)
WHERE {
  ?p wdt:P106 wd:%(occ)s; wdt:P31 wd:Q5; wdt:P569 ?b .
  BIND(YEAR(?b) AS ?birth)
  FILTER(?birth >= %(bmin)d && ?birth <= %(bmax)d)
  ?a schema:about ?p; schema:isPartOf <https://en.wikipedia.org/>; schema:name ?title .
  OPTIONAL { ?p wdt:P21 ?g }
  OPTIONAL { ?p wdt:P496 ?orcid_ }
  OPTIONAL { ?p wdt:P10283 ?oa_ }
  OPTIONAL { ?p rdfs:label ?label_ FILTER(LANG(?label_) = "en") }
} GROUP BY ?p ?title ?birth
"""

GENDER = {"Q6581097": "male", "Q6581072": "female"}


def run():
    frames = []
    for occ, field in FIELDS.items():
        q = TEMPLATE % {"occ": occ, "bmin": BIRTH_MIN, "bmax": BIRTH_MAX}
        r = get(ENDPOINT, params={"query": q, "format": "json"})
        rows = []
        for b in r.json()["results"]["bindings"]:
            gs = [g.rsplit("/", 1)[-1] for g in b.get("genders", {}).get("value", "").split("|") if g]
            labels = {GENDER.get(g, "other") for g in gs}
            gender = labels.pop() if len(labels) == 1 else ("missing" if not labels else "multiple")
            rows.append({
                "qid": b["p"]["value"].rsplit("/", 1)[-1],
                "title": b["title"]["value"],
                "label": b.get("label", {}).get("value"),
                "birth_year": int(float(b["birth"]["value"])),
                "gender": gender,
                "orcid": b.get("orcid", {}).get("value"),
                "openalex_wd": b.get("openalex", {}).get("value"),
                "field": field,
            })
        df = pd.DataFrame(rows)
        log("Wikidata SPARQL", f"occupation={occ} ({field}), birth {BIRTH_MIN}-{BIRTH_MAX}, enwiki page", len(df))
        print(f"{field}: {len(df)} people")
        frames.append(df)

    df = pd.concat(frames)
    # People with several occupations appear in several fields: keep one row, list all fields.
    fields = df.groupby("qid")["field"].apply(lambda s: "|".join(sorted(set(s))))
    df = df.drop_duplicates("qid").drop(columns="field").merge(fields, on="qid")
    # Some people share a birth-year-ambiguous record; keep the first.
    df = df.drop_duplicates("title")
    df.to_csv(PROC / "scientists_wikidata.csv", index=False)
    print(df.groupby("gender").size())
    print(f"Total unique people: {len(df)}; with ORCID: {df.orcid.notna().sum()}; "
          f"with OpenAlex ID: {df.openalex_wd.notna().sum()}")
    log("Wikidata SPARQL", "merged unique people across fields", len(df))


if __name__ == "__main__":
    run()
