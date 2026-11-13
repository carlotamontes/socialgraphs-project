# Who Gets Remembered? (analysis pipeline)

The single-notebook version (`who_gets_remembered.ipynb`) is shared separately.
Gender, scientific impact and visibility on scientists' Wikipedia pages: DTU 02805 final project.

Plan: `project_plan_women_scientists.pdf`. Phase 0 decisions: `docs/scope_note.md`.

## Pipeline
Run from `src/`, with the project venv:
```bash
cd src
../.venv/bin/python 01_wikidata.py      # 1a  scientist list, gender, birth year, ORCID/OpenAlex IDs
../.venv/bin/python 02_wikipedia.py     # 1b  wikitext, redirects, edges, plain text
../.venv/bin/python 03_openalex.py      # 1c  citations, works, h-index via ORCID / OpenAlex IDs
../.venv/bin/python 04_enrich.py        # 1d  awards + Nobel + deceased (Wikidata), pageviews, all-wiki backlinks
../.venv/bin/python 05_clean.py         # 2   merge, clean, strata, hand-check sample, cleaning report
../.venv/bin/python 06_network.py       # 3   RQ1 stratified shuffle + regression, RQ3, Figures 1 and 3
../.venv/bin/python 07_text.py          # 4   RQ2 masking, word lists, Fightin' Words, Figure 2, labelling sample
../.venv/bin/python 07_text.py --validate   # after hand labels are filled in
../.venv/bin/python 08_robustness.py    # 5   robustness table (bins, seeds, impact measure, no Nobel, no top 1%, biology)
```

### Design choices (from the plan review)
- **Strata:** RQ1 shuffles gender within field × birth decade × impact bin, not citations alone.
- **Regression:** log outcome ~ female + log impact + field + decade + deceased (HC3 95% CI); a second model adds Nobel + awards to see how much of the gap runs through prizes.
- **Visibility outcomes:** PageRank, in-degree, page length. Pageviews and all-Wikipedia in-links (`04_enrich.py views backlinks`) were dropped: Wikimedia rate-limited us (HTTP 429), and the group decided they are not essential. Mention as a limitation / future work.
- **Impact:** citations (main), h-index and works (robustness); top 1% and Nobel laureates dropped in robustness runs. We estimate the gap *on top of* existing inequality in citations, not net of it.
- **Matching:** ID-only (ORCID / OpenAlex ID). Match accuracy and profile completeness are reported separately for women and men (hand-check sample, 50 + 50).
- **Text:** names masked with spaCy NER; pronouns and gender words masked; kinship words made gender-neutral. Fightin' Words (Monroe et al. 2008) on document frequencies. Word lists validated on a stratified, weighted sample of ~150 sentences per gender.
- **RQ3:** one number, the share of in-links to women's pages that come from women, against a within field × decade shuffle. Communities are descriptive only (Figure 3).
- **Not done yet:** selection into Wikipedia (top-cited OpenAlex authors with/without a page), only if time allows after M2.

## Data
| File | Content |
|---|---|
| `data/processed/scientists_wikidata.csv` | Wikidata list (qid, title, gender, birth_year, orcid, field) |
| `data/processed/edges.csv` / `edges_clean.csv` | directed hyperlinks between scientists' pages |
| `data/processed/text/<qid>.txt` | plain text, reference sections removed |
| `data/processed/impact.csv` | OpenAlex citations, works, h-index, match method |
| `data/processed/nodes.csv` | cleaned node table with all attributes |
| `data/processed/awards.csv`, `pageviews.csv`, `backlinks.csv` | enrichment from Wikidata / Wikimedia |
| `data/processed/handcheck_sample.csv` | 100 matches (50 women, 50 men) to verify by hand: `correct`, `profile_complete` |
| `results/sentences_to_label.csv` | sentences to hand-label: `is_personal`, `is_professional` |
| `data/data_log.csv` | every query, date and record count |
| `data/raw/` | raw downloads (wikitext per page, OpenAlex author records) |

Results go to `results/`, figures to `figures/`.
