"""Phase 1d: extra node attributes suggested in the plan review.

  awards   Wikidata P166 (number of awards, Nobel Prize flag), P570 (deceased)     -> point 3, point 5
  views    Wikipedia pageviews, last 60 days (PageViewInfo API)                    -> point 4: direct visibility
  backlinks  in-links from ALL of English Wikipedia (articles, incl. via redirects) -> point 4: robustness of in-degree

Usage: python 04_enrich.py [awards] [views] [backlinks]   (default: all)
Outputs: data/processed/awards.csv, pageviews.csv, backlinks.csv. Raw results are cached so runs can resume.
"""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from tqdm import tqdm

from common import PROC, RAW, get, log

NOBEL = {"Q38104": "physics", "Q44585": "chemistry", "Q80061": "medicine"}
_lock = threading.Lock()


def people():
    return pd.read_csv(PROC / "scientists_wikidata.csv")


def awards():
    p = people()
    rows = []
    q = """SELECT ?p (COUNT(DISTINCT ?aw) AS ?n_awards) (GROUP_CONCAT(DISTINCT ?nb; separator="|") AS ?nobel)
                  (SAMPLE(?d) AS ?death) WHERE {
             VALUES ?p { %s }
             OPTIONAL { ?p wdt:P166 ?aw }
             OPTIONAL { ?p wdt:P166 ?nb . VALUES ?nb { wd:Q38104 wd:Q44585 wd:Q80061 } }
             OPTIONAL { ?p wdt:P570 ?d }
           } GROUP BY ?p"""
    ids = list(p.qid)
    for i in tqdm(range(0, len(ids), 300), desc="awards"):
        vals = " ".join(f"wd:{x}" for x in ids[i:i + 300])
        r = get("https://query.wikidata.org/sparql", params={"query": q % vals, "format": "json"}, pause=0.5)
        for b in r.json()["results"]["bindings"]:
            nob = [x.rsplit("/", 1)[-1] for x in b.get("nobel", {}).get("value", "").split("|") if x]
            rows.append({"qid": b["p"]["value"].rsplit("/", 1)[-1], "n_awards": int(b["n_awards"]["value"]),
                         "nobel": int(bool(nob)), "nobel_fields": "|".join(NOBEL[n] for n in nob),
                         "deceased": int("death" in b)})
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "awards.csv", index=False)
    log("Wikidata SPARQL", "P166 awards, Nobel flag, P570 death for all people", len(df),
        f"nobel={df.nobel.sum()}, deceased={df.deceased.sum()}")
    print(df[["n_awards", "nobel", "deceased"]].describe().loc[["mean", "max"]])


def _cached_parallel(name, items, fn, workers=4):
    """Run fn(qid, title) -> dict for each item, caching one JSON line per item."""
    cache = RAW / f"{name}.jsonl"
    done = {}
    if cache.exists():
        for line in cache.open():
            d = json.loads(line)
            done[d["qid"]] = d
    todo = [(q, t) for q, t in items if q not in done]

    def run(q, t):
        try:
            d = {"qid": q, **fn(t)}
        except Exception as e:  # keep going; failures are logged and retried on the next run
            return {"qid": q, "error": str(e)[:200]}
        with _lock, cache.open("a") as f:
            f.write(json.dumps(d) + "\n")
        return d

    errors = 0
    with ThreadPoolExecutor(workers) as ex:
        for d in tqdm(ex.map(lambda x: run(*x), todo), total=len(todo), desc=name, mininterval=20):
            if "error" in d:
                errors += 1
            else:
                done[d["qid"]] = d
    return pd.DataFrame(done.values()), errors


def views():
    """Daily user pageviews, last 60 days, via the PageViewInfo API (50 titles per request).
    The per-article REST endpoint rate-limited us (HTTP 429), so we use this batched source instead."""
    p = people()
    by_title = dict(zip(p.title, p.qid))
    titles = list(p.title)
    cache = RAW / "pageviews_60d.jsonl"
    rows = {}
    if cache.exists():
        for line in cache.open():
            d = json.loads(line)
            rows[d["qid"]] = d
    done_titles = {t for t in titles if by_title[t] in rows}
    titles = [t for t in titles if t not in done_titles]
    print(f"pageviews: {len(rows)} cached, {len(titles)} to fetch", flush=True)
    for i in range(0, len(titles), 50):
        if i % 1000 == 0:
            print(f"  {i}/{len(titles)}", flush=True)
        batch, cont = titles[i:i + 50], {}
        while True:
            r = get("https://en.wikipedia.org/w/api.php",
                    params={"action": "query", "prop": "pageviews", "titles": "|".join(batch), "pvipdays": 60,
                            "redirects": 1, "format": "json", "formatversion": 2, "maxlag": 5, **cont}, pause=0.1)
            j = r.json()
            q = j["query"]
            alias = {x["from"]: x["to"] for x in q.get("normalized", []) + q.get("redirects", [])}
            back = {}
            for t in batch:
                c = t
                while c in alias:
                    c = alias[c]
                back[c] = t
            for pg in q["pages"]:
                if "pageviews" in pg:
                    qid = by_title.get(back.get(pg["title"], pg["title"]))
                    if qid:
                        rows[qid] = {"qid": qid, "pageviews_60d": sum(v or 0 for v in pg["pageviews"].values()),
                                     "pageview_days": len(pg["pageviews"])}
                        with cache.open("a") as fh:
                            fh.write(json.dumps(rows[qid]) + "\n")
            if "continue" not in j:
                break
            cont = j["continue"]
    df = pd.DataFrame(rows.values())
    df.to_csv(PROC / "pageviews.csv", index=False)
    log("Wikipedia API", "prop=pageviews (PageViewInfo), last 60 days, all people", len(df))
    print("pageviews:", len(df), "of", len(p), "median:", df.pageviews_60d.median())


def _backlinks(title):
    n, cont = 0, {}
    while True:
        r = get("https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "backlinks", "bltitle": title, "blnamespace": 0,
                        "bllimit": "max", "blredirect": 1, "blfilterredir": "nonredirects",
                        "format": "json", "formatversion": 2, "maxlag": 5, **cont})
        j = r.json()
        for b in j["query"]["backlinks"]:
            n += 1 + len(b.get("redirlinks", []))
        if "continue" not in j:
            return {"backlinks_enwiki": n}
        cont = j["continue"]


def backlinks():
    """Only for people matched to OpenAlex (the comparison set); full-wiki in-links are a robustness check."""
    p = people().merge(pd.read_csv(PROC / "impact.csv")[["qid"]], on="qid")
    df, err = _cached_parallel("backlinks", list(zip(p.qid, p.title)), _backlinks, workers=1)
    df[["qid", "backlinks_enwiki"]].to_csv(PROC / "backlinks.csv", index=False)
    log("Wikipedia API", "list=backlinks (ns 0, incl. via redirects) for matched people", len(df), f"errors={err}")
    print("backlinks:", len(df), "errors:", err, "median:", df.backlinks_enwiki.median())


if __name__ == "__main__":
    steps = sys.argv[1:] or ["awards", "views", "backlinks"]
    for s in steps:
        {"awards": awards, "views": views, "backlinks": backlinks}[s]()
