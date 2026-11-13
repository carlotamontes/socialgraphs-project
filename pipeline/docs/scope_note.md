# Scope note (Phase 0) — 13 Nov 2026

## Fixed choices
- **Fields:** physics (Wikidata Q169470) and chemistry (Q593644) are the main analysis. Biology (Q864503) is collected for the robustness check (Phase 5).
- **Birth years:** 1920–1980 (inclusive), from P569. People with several birth dates are kept once.
- **Membership:** Wikidata humans (P31=Q5) with that occupation (P106) and an English Wikipedia sitelink.
- **Gender:** P21. Only `male` and `female` are compared; other values (11 people) and missing values (1) are kept as network nodes but excluded from the gender comparisons. This is stated in Methods.
- **Impact:** OpenAlex author records, matched **only through identifiers stored in Wikidata** (OpenAlex ID P10283 first, then ORCID P496). No name matching in the main analysis.

## Why ID-only matching
- It removes most name ambiguity (the main risk in Section 7 of the plan).
- OpenAlex now limits keyless use to about $0.10 a day. A name search costs $0.001, so that is about 100 searches a day, far too few for around 8,000 unmatched people.
- **Known bias to report:** ORCID coverage is higher for women (44% in the main fields) than for men (30%) and for people born later, so the matched set is younger and has a larger share of women than the full set. The comparisons are within citation bins and the regression controls for birth decade, but the matched set is not a random sample of Wikipedia scientists. We say this in Methods.
- **Split profiles:** in ~600 cases one ORCID maps to several OpenAlex author profiles. We add up citations and works across them (`n_profiles` > 1 is flagged) and check this in the hand-check sample.

## Initial counts (13 Nov 2026)
| | All fields | Physics + chemistry |
|---|---|---|
| People on Wikidata with enwiki page | 12,773 | ~9,900 |
| Women | 2,279 | 1,473 |
| Matched to OpenAlex by ID (any gender) | 4,146 | ~3,150 |
| Women matched | 996 | 647 |

**M1 condition (≥100 women matched):** met on ID matching alone.

## Network size vs. the 1,500–3,000 target
The full physics + chemistry page set (~9,900 nodes) is larger than the course range. The **network** uses all pages, because centrality depends on the whole link structure. The **comparison set** for RQ1/RQ2 is the matched subset (~3,000), which is inside the range. If the network needs to be smaller for figures or runtime, we use the largest weakly connected component.

## Open decisions for the group
- [ ] Confirm roles (Section 9 of the plan).
- [ ] Optional: get a free OpenAlex API key (openalex.org/settings/api) and set `OPENALEX_API_KEY` if we later want first-publication years or name-matching as a robustness check.
