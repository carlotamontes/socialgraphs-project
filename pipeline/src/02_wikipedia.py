"""Phase 1b: English Wikipedia wikitext, redirects, hyperlink network and plain text.

Outputs:
  data/raw/wikitext/<qid>.wiki          raw wikitext per page
  data/processed/redirects.csv          redirect title -> canonical title
  data/processed/edges.csv              directed links between pages in the set (source_qid, target_qid)
  data/processed/text/<qid>.txt         plain text, reference-type sections removed
  data/processed/pages.csv              qid, title, n_chars, n_words, n_out_links_all
"""
import re
import json

import mwparserfromhell as mwp
import pandas as pd
from tqdm import tqdm

from common import PROC, RAW, get, log

API = "https://en.wikipedia.org/w/api.php"
WT = RAW / "wikitext"
TXT = PROC / "text"
TXT.mkdir(exist_ok=True)

DROP_SECTIONS = {"references", "notes", "external links", "further reading", "see also",
                 "bibliography", "sources", "citations", "footnotes", "notes and references",
                 "selected publications", "publications", "selected works", "works",
                 "selected bibliography", "references and notes"}


def norm(t):
    t = t.split("#", 1)[0].replace("_", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


def chunks(xs, n=50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def _fetch_one(qid, title):
    """Raw wikitext for one page; follows one redirect level if the sitelink is a redirect."""
    for _ in range(2):
        r = get("https://en.wikipedia.org/w/index.php", params={"title": title, "action": "raw"})
        m = re.match(r"#REDIRECT\s*\[\[([^\]|#]+)", r.text, re.I)
        if not m:
            (WT / f"{qid}.wiki").write_text(r.text)
            return True
        title = m.group(1)
    return False


def fetch_wikitext(people, workers=4):
    # Single-page raw fetches with a few parallel workers: multi-title prop=revisions
    # took ~45 s per 50 pages, this takes ~0.5 s per page.
    from concurrent.futures import ThreadPoolExecutor
    todo = people[~people.qid.map(lambda q: (WT / f"{q}.wiki").exists())]
    fails = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(_fetch_one, q, t) for q, t in zip(todo.qid, todo.title)]
        for f in tqdm(futs, desc="wikitext", mininterval=30):
            try:
                fails += not f.result()
            except Exception:
                fails += 1
    log("Wikipedia", "index.php?action=raw for all scientist titles",
        sum(1 for _ in WT.glob("*.wiki")), f"failed={fails}")


def fetch_redirects(people):
    out = PROC / "redirects.csv"
    if out.exists():
        return pd.read_csv(out)
    rows = []
    for batch in tqdm(list(chunks(list(people.title))), desc="redirects"):
        cont = {}
        while True:
            r = get(API, params={"action": "query", "prop": "redirects", "rdlimit": "max",
                                 "rdnamespace": 0, "titles": "|".join(batch), "format": "json",
                                 "formatversion": 2, "maxlag": 5, **cont}, pause=0.1)
            j = r.json()
            for p in j["query"]["pages"]:
                for rd in p.get("redirects", []):
                    rows.append({"redirect": rd["title"], "target": p["title"]})
            if "continue" not in j:
                break
            cont = j["continue"]
    df = pd.DataFrame(rows).drop_duplicates()
    df.to_csv(out, index=False)
    log("Wikipedia API", "prop=redirects (ns 0) for all scientist titles", len(df))
    return df


def plain_text(code):
    """Strip wikitext to prose; drop reference-like sections, tables, infobox, refs."""
    keep = []
    for sec in code.get_sections(levels=[2], include_lead=True, flat=False):
        heads = sec.filter_headings()
        if heads and heads[0].title.strip_code().strip().lower() in DROP_SECTIONS:
            continue
        keep.append(str(sec))
    code = mwp.parse("\n".join(keep))
    for tag in code.filter_tags(recursive=True):
        if str(tag.tag).lower() in ("ref", "table", "gallery", "math", "references"):
            try:
                code.remove(tag)
            except ValueError:
                pass
    for tpl in code.filter_templates(recursive=False):
        try:
            code.remove(tpl)
        except ValueError:
            pass
    text = code.strip_code(normalize=True, collapse=True)
    text = re.sub(r"\[\[(File|Image|Category):[^\]]*\]\]", "", text, flags=re.I)
    text = re.sub(r"^\s*(thumb|left|right|upright)\|.*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build(people, redirects):
    canon = dict(zip(people.title.map(norm), people.qid))
    for a, b in zip(redirects.redirect, redirects.target):
        if norm(b) in canon:
            canon[norm(a)] = canon[norm(b)]
    edges, stats = set(), []
    for qid, title in tqdm(list(zip(people.qid, people.title)), desc="parse"):
        f = WT / f"{qid}.wiki"
        if not f.exists():
            continue
        raw = f.read_text()
        code = mwp.parse(raw)
        links = [norm(str(l.title)) for l in code.filter_wikilinks()]
        bad = {"file", "image", "category", "wikipedia", "template", "help", "portal", "wikt"}
        links = [l for l in links if l and l.split(":")[0].lower() not in bad]
        for l in links:
            t = canon.get(l)
            if t and t != qid:
                edges.add((qid, t))
        text = plain_text(code)
        (TXT / f"{qid}.txt").write_text(text)
        stats.append({"qid": qid, "title": title, "n_chars": len(text), "n_words": len(text.split()),
                      "n_links_all": len(set(links)),
                      "is_redirect_or_disambig": bool(re.match(r"#REDIRECT", raw, re.I)) or
                      bool(re.search(r"\{\{\s*(disambiguation|dab|hndis|set index)", raw, re.I))})
    e = pd.DataFrame(sorted(edges), columns=["source", "target"])
    e.to_csv(PROC / "edges.csv", index=False)
    pd.DataFrame(stats).to_csv(PROC / "pages.csv", index=False)
    log("derived", "edges from wikilinks within the scientist set (redirects resolved)", len(e))
    print(f"pages parsed: {len(stats)}, edges: {len(e)}")


if __name__ == "__main__":
    people = pd.read_csv(PROC / "scientists_wikidata.csv")
    fetch_wikitext(people)
    red = fetch_redirects(people)
    build(people, red)
