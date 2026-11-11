# Who Gets Remembered? — data collection (Phase 1)

Three scripts, run in order from inside the `project/` folder. Each one is safe to
re-run: what's already downloaded is cached in `data/raw/` and skipped.

| Step | Script | Source | Produces |
|---|---|---|---|
| 1 | `src/01_wikidata.py` | Wikidata SPARQL | `data/wikidata_scientists.csv` (who, gender, birth year, ORCID, OpenAlex ID) |
| 2 | `src/02_wikipedia.py` | Wikipedia API | `data/nodes.csv`, `data/edges.csv`, `data/text/<qid>.txt` |
| 3 | `src/03_openalex.py` | OpenAlex API | `data/impact.csv`, `data/raw/openalex_name_candidates.jsonl` |

Every query is appended to `data/data_log.csv` (date, source, what, how many records).

## Setup (once)

```powershell
cd project
pip install -r requirements.txt
copy .env.example .env      # then open .env and fill in the two lines
```

- `CONTACT_EMAIL` — Wikimedia asks scripts to identify themselves with a contact.
- `OPENALEX_API_KEY` — free, required since Feb 2026: make an account at openalex.org, copy the key from openalex.org/settings/api.

`.env` is git-ignored, so the key never goes to GitHub.

## Run

```powershell
python src/01_wikidata.py                 # ~1 min. Prints counts by field and gender
python src/02_wikipedia.py --limit 100    # quick test first
python src/02_wikipedia.py                # everyone (~5-10 min for 3,000 pages)
python src/03_openalex.py --limit 50      # quick test first
python src/03_openalex.py                 # everyone
```

**Check scope after step 1.** The plan targets 1,500–3,000 nodes. If step 1 gives far
more, narrow it *before* step 2 (one field, or a shorter birth range), for example
`python src/01_wikidata.py --fields physicist --min-year 1930 --max-year 1975`.
Don't subsample nodes at random afterwards: that cuts links and distorts the network.
If it gives too few women, widen with `--subclasses` (adds e.g. "theoretical physicist").

## Decisions worth writing in Methods

- **Who counts:** humans with occupation (P106) = physicist / chemist directly (not sub-occupations unless `--subclasses`), born 1920–1980, with an English Wikipedia page.
- **Gender:** Wikidata P21 as recorded; `missing` and `multiple` are kept in the file and reported, not guessed.
- **Links:** `[[wikilinks]]` written in the page source, including the infobox (e.g. doctoral advisor), but **not** navbox templates, which aren't expanded. Redirects are resolved; self-links are dropped. `n_links` = how many times the link appears.
- **Text:** references, templates/infobox, tables, files and categories removed; everything from the first References / Notes / See also / External links / (Selected) publications heading onward is cut.
- **Impact:** only via IDs that Wikidata provides (OpenAlex ID first, then ORCID). If one person has several OpenAlex profiles, the one with the most works is kept and `n_openalex_profiles` records the split. `name_similarity` flags suspicious ID matches.
- **People with no ID:** the top 5 name-search candidates are saved but **not** used. Picking among them is Phase 2, with a hand-checked sample of 100.
- **Snapshot:** `nodes.csv` stores each page's `revid` and timestamp, so the exact version can be cited.

## Output columns

- `nodes.csv`: qid, title, gender, birth_year, fields, orcid, openalex_id, birth_year_conflict, wiki_title, n_chars, n_words, n_links_total, revid, rev_timestamp
- `edges.csv`: source_qid, target_qid, n_links (directed: source links to target)
- `impact.csv`: qid, match_method, n_openalex_profiles, first_pub_year, openalex_id, oa_display_name, oa_orcid, works_count, cited_by_count, h_index, i10_index, top_topic, top_field, last_institution, name_similarity
