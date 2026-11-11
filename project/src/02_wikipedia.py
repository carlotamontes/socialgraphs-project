"""Step 2 - English Wikipedia: page text and links between scientists.

For every person in data/wikidata_scientists.csv:
  1. download the page's wikitext (20 pages per API call)  -> data/raw/wikitext/<qid>.wiki
  2. collect all redirects that point to our pages, so a link to "Marie Sklodowska Curie"
     still lands on "Marie Curie"
  3. parse [[wikilinks]] written in each page (navbox templates are NOT expanded,
     so the big "Nobel laureates" boxes don't create fake links)
  4. clean the text: drop <ref>s, templates (infobox), tables, and trailing sections
     (References, External links, Selected publications ...)  -> data/text/<qid>.txt

Outputs: data/nodes.csv   (one row per page that exists)
         data/edges.csv   (source_qid, target_qid, n_links)  directed, no self-loops

Re-running is safe: pages already on disk are not downloaded again
(use --refresh to force).

Usage:
    python src/02_wikipedia.py --limit 100   # quick test on 100 people
    python src/02_wikipedia.py               # everyone
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter

import mwparserfromhell
import pandas as pd

from common import DATA, RAW, TEXT, chunks, log_query, make_session, request_json

API = "https://en.wikipedia.org/w/api.php"
WIKITEXT_DIR = RAW / "wikitext"
WIKITEXT_DIR.mkdir(parents=True, exist_ok=True)
PAUSE = 0.5   # seconds between API calls - be polite (as in the Marvel exercise)
BATCH = 20    # titles per call; long pages in big batches can hit the API's size limit

CUT_SECTIONS = {
    "references", "notes", "footnotes", "citations", "sources", "notes and references",
    "references and notes", "external links", "see also", "further reading",
    "bibliography", "selected bibliography", "publications", "selected publications",
    "selected works", "works", "books", "patents",
}
DROP_TAGS = {"ref", "references", "gallery", "math", "chem", "ce", "score",
             "timeline", "syntaxhighlight", "source", "imagemap", "table"}


# ---------------------------------------------------------------- helpers
def normalize_title(t: str) -> str:
    """Make a link target comparable with a page title."""
    t = t.split("#", 1)[0].replace("_", " ").strip().lstrip(":")
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


def api_query(session, params: dict) -> dict:
    """MediaWiki query with maxlag handling."""
    base = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5}
    for attempt in range(6):
        res = request_json(session, API, params={**base, **params})
        err = (res or {}).get("error", {})
        if err.get("code") == "maxlag":
            time.sleep(5 * (attempt + 1))
            continue
        if err:
            raise RuntimeError(err)
        return res
    raise RuntimeError("maxlag retries exhausted")


def fetch_wikitext(session, titles: list[str]) -> tuple[dict, dict]:
    """Returns ({requested_title: final_title}, {final_title: page_info})."""
    res = api_query(session, {
        "prop": "revisions|pageprops",
        "rvprop": "content|ids|timestamp",
        "rvslots": "main",
        "ppprop": "disambiguation",
        "redirects": 1,
        "titles": "|".join(titles),
    })
    q = res.get("query", {})
    mapping = {t: t for t in titles}
    for step in ("normalized", "redirects"):
        for m in q.get(step, []):
            for k, v in mapping.items():
                if v == m["from"]:
                    mapping[k] = m["to"]
    pages = {}
    for p in q.get("pages", []):
        info = {"title": p["title"], "missing": "missing" in p or "invalid" in p,
                "pageid": p.get("pageid"),
                "disambiguation": "disambiguation" in p.get("pageprops", {})}
        if p.get("revisions"):
            rev = p["revisions"][0]
            info["wikitext"] = rev["slots"]["main"]["content"]
            info["revid"] = rev.get("revid")
            info["rev_timestamp"] = rev.get("timestamp")
        pages[p["title"]] = info
    return mapping, pages


def fetch_redirects(session, titles: list[str]) -> dict[str, str]:
    """{redirect_title: target_title} for all redirects pointing at `titles`."""
    out = {}
    cont = {}
    while True:
        res = api_query(session, {"prop": "redirects", "rdlimit": "max",
                                  "rdnamespace": 0, "titles": "|".join(titles), **cont})
        for p in res.get("query", {}).get("pages", []):
            for r in p.get("redirects", []):
                out[r["title"]] = p["title"]
        if "continue" not in res:
            return out
        cont = res["continue"]
        time.sleep(PAUSE)


def extract_links(wikitext: str) -> list[str]:
    """Normalised targets of every [[link]] written in the page source."""
    code = mwparserfromhell.parse(wikitext)
    return [normalize_title(str(l.title)) for l in code.filter_wikilinks()]


def clean_text(wikitext: str) -> str:
    """Plain prose of the article body (no refs, infobox, tables, link lists)."""
    # cut everything from the first 'References'-type level-2 heading onwards
    # (done on the raw text: some headings sit inside <div>s, where the parser
    #  can't index them)
    for m in re.finditer(r"^==\s*([^=].*?)\s*==\s*$", wikitext, flags=re.M):
        if m.group(1).strip().lower() in CUT_SECTIONS:
            wikitext = wikitext[:m.start()]
            break
    code = mwparserfromhell.parse(wikitext)
    for tag in code.filter_tags(recursive=False):
        if str(tag.tag).lower() in DROP_TAGS:
            try:
                code.remove(tag)
            except ValueError:
                pass
    for tpl in code.filter_templates(recursive=False):
        try:
            code.remove(tpl)
        except ValueError:
            pass
    for link in code.filter_wikilinks(recursive=False):
        if re.match(r"\s*:?\s*(file|image|category)\s*:", str(link.title), re.I):
            try:
                code.remove(link)
            except ValueError:
                pass
    text = code.strip_code(normalize=True, collapse=True)
    text = re.sub(r"\{\|.*?\|\}", " ", text, flags=re.S)        # leftover wiki tables
    text = re.sub(r"^(thumb|left|right|upright)\|.*$", "", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N people (for testing)")
    ap.add_argument("--refresh", action="store_true", help="re-download all pages")
    args = ap.parse_args()

    people = pd.read_csv(DATA / "wikidata_scientists.csv", dtype=str)
    if args.limit:
        people = people.head(args.limit)
    session = make_session()

    # 1. wikitext ------------------------------------------------------
    meta_file = RAW / "wikipedia_pages_meta.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    todo = people if args.refresh else people[~people.qid.isin(meta.keys())]
    print(f"Downloading wikitext for {len(todo)} pages "
          f"({len(people) - len(todo)} already on disk) ...")
    n_batches = (len(todo) + BATCH - 1) // BATCH
    n_retry = 0
    for i, batch in enumerate(chunks(list(todo.itertuples()), BATCH), 1):
        mapping, pages = fetch_wikitext(session, [p.title for p in batch])
        for p in batch:
            info = pages.get(mapping.get(p.title, p.title), {"missing": True})
            if "wikitext" in info:
                (WIKITEXT_DIR / f"{p.qid}.wiki").write_text(info["wikitext"], encoding="utf-8")
            elif not info.get("missing"):
                n_retry += 1          # content left out of this answer: try next run
                continue
            meta[p.qid] = {k: v for k, v in info.items() if k != "wikitext"}
            meta[p.qid].setdefault("title", p.title)
        meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        print(f"  batch {i}/{n_batches}", end="\r")
        time.sleep(PAUSE)
    print()
    if n_retry:
        print(f"NOTE: {n_retry} pages came back without text - just run the script again.")
    log_query("Wikipedia API", "wikitext (prop=revisions) for scientists' pages",
              sum(1 for q in people.qid if not meta.get(q, {}).get("missing", True)),
              f"{len(todo)} requested this run")

    ok = people[people.qid.map(lambda q: not meta.get(q, {}).get("missing", True)
                               and not meta.get(q, {}).get("disambiguation", False)
                               and (WIKITEXT_DIR / f"{q}.wiki").exists())].copy()
    ok["wiki_title"] = ok.qid.map(lambda q: meta[q]["title"])
    print(f"{len(ok)} pages exist and are not disambiguation pages "
          f"({len(people) - len(ok)} dropped)")

    # 2. redirects -> our pages ---------------------------------------
    title_to_qid = {normalize_title(t): q for q, t in zip(ok.qid, ok.wiki_title)}
    redir_file = RAW / "wikipedia_redirects.json"
    redirects = json.loads(redir_file.read_text(encoding="utf-8")) if redir_file.exists() else {}
    missing_redirs = [t for t in ok.wiki_title if t not in redirects.get("_done", [])]
    if missing_redirs:
        print(f"Fetching redirects for {len(missing_redirs)} pages ...")
        done = set(redirects.get("_done", []))
        for batch in chunks(missing_redirs, 50):
            redirects.update(fetch_redirects(session, batch))
            done.update(batch)
            time.sleep(PAUSE)
        redirects["_done"] = sorted(done)
        redir_file.write_text(json.dumps(redirects, ensure_ascii=False), encoding="utf-8")
        log_query("Wikipedia API", "redirects pointing to scientists' pages (prop=redirects)",
                  len(redirects) - 1)
    alias_to_qid = dict(title_to_qid)
    for src, tgt in redirects.items():
        if src != "_done" and normalize_title(tgt) in title_to_qid:
            alias_to_qid[normalize_title(src)] = title_to_qid[normalize_title(tgt)]

    # 3 + 4. links and text --------------------------------------------
    edges = Counter()
    n_out_all = {}
    stats = []
    for q in ok.qid:
        wt = (WIKITEXT_DIR / f"{q}.wiki").read_text(encoding="utf-8")
        links = extract_links(wt)
        n_out_all[q] = len(set(links))
        for t in links:
            tq = alias_to_qid.get(t)
            if tq and tq != q:
                edges[(q, tq)] += 1
        try:
            txt = clean_text(wt)
        except Exception as e:          # never let one odd page stop the run
            print(f"  text cleaning failed for {q}: {e!r}; using plain strip")
            txt = mwparserfromhell.parse(wt).strip_code()
        (TEXT / f"{q}.txt").write_text(txt, encoding="utf-8")
        stats.append({"qid": q, "n_chars": len(txt), "n_words": len(txt.split()),
                      "n_links_total": n_out_all[q]})

    edges_df = pd.DataFrame([(s, t, n) for (s, t), n in edges.items()],
                            columns=["source_qid", "target_qid", "n_links"])
    edges_df.to_csv(DATA / "edges.csv", index=False, encoding="utf-8")

    nodes = ok.merge(pd.DataFrame(stats), on="qid")
    nodes["revid"] = nodes.qid.map(lambda q: meta[q].get("revid"))
    nodes["rev_timestamp"] = nodes.qid.map(lambda q: meta[q].get("rev_timestamp"))
    nodes.to_csv(DATA / "nodes.csv", index=False, encoding="utf-8")
    log_query("derived", "nodes.csv / edges.csv from wikitext links",
              len(edges_df), f"{len(nodes)} nodes")

    indeg = edges_df.target_qid.value_counts()
    nodes["in_degree"] = nodes.qid.map(indeg).fillna(0)
    print(f"\nnodes.csv: {len(nodes)} pages   edges.csv: {len(edges_df)} links")
    print(f"Pages with no in-links from the set: {(nodes.in_degree == 0).mean():.1%}")
    print("\nMean in-degree by gender:")
    print(nodes.groupby("gender")["in_degree"].agg(["count", "mean"]).round(2).to_string())
    print("\nMost linked-to pages:")
    print(nodes.nlargest(10, "in_degree")[["wiki_title", "gender", "in_degree"]].to_string(index=False))


if __name__ == "__main__":
    main()
