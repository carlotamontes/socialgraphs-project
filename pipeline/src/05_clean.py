"""Phase 2: merge, clean, define strata, and draw the hand-check sample.

Outputs:
  data/processed/nodes.csv                 all pages kept, with every attribute
  data/processed/edges_clean.csv           links between kept pages
  data/processed/handcheck_sample.csv      100 matches (50 women, 50 men) to verify by hand: fill `correct` 1/0
  data/processed/cleaning_report.txt       counts at each step + match quality by gender (for Methods)
"""
import numpy as np
import pandas as pd

from common import MAIN_FIELDS, PROC, log

SEED = 2805


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def field_group(fields):
    fs = set(fields.split("|"))
    main = fs & MAIN_FIELDS
    if main == {"physics", "chemistry"}:
        return "phys+chem"
    if main:
        return main.pop()
    return "biology"


def optional(name, cols):
    f = PROC / name
    if f.exists():
        return pd.read_csv(f)
    print(f"  (note: {name} not found yet; columns {cols} will be missing)")
    return pd.DataFrame(columns=["qid"] + cols)


def run():
    people = pd.read_csv(PROC / "scientists_wikidata.csv")
    pages = pd.read_csv(PROC / "pages.csv")
    impact = pd.read_csv(PROC / "impact.csv")
    edges = pd.read_csv(PROC / "edges.csv")
    rep = []

    def note(msg, n=""):
        rep.append(f"{msg}: {n}" if n != "" else msg)
        print(rep[-1])

    note("Wikidata people (all fields)", len(people))
    df = people.merge(pages.drop(columns="title"), on="qid", how="inner")
    note("with downloaded Wikipedia page", len(df))
    df = df[~df.is_redirect_or_disambig]
    note("after removing redirects / disambiguation pages", len(df))
    df = df[df.n_words >= 50]
    note("after removing stubs (< 50 words of prose)", len(df))

    df["gender_known"] = df.gender.isin(["male", "female"])
    df["field_group"] = df.field.map(field_group)
    df["main_field"] = df.field_group != "biology"
    df["birth_decade"] = (df.birth_year // 10 * 10).astype(int)

    df = (df.merge(impact, on="qid", how="left")
            .merge(optional("awards.csv", ["n_awards", "nobel", "nobel_fields", "deceased"]), on="qid", how="left")
            .merge(optional("pageviews.csv", ["pageviews_60d"]), on="qid", how="left")
            .merge(optional("backlinks.csv", ["backlinks_enwiki"]), on="qid", how="left"))
    df["matched"] = df.openalex_id.notna()
    df["match_doubtful"] = df.matched & (df.name_similarity < 0.6)
    df["usable"] = df.matched & ~df.match_doubtful & df.gender_known & (df.citations > 0)

    note("")
    note("Gender (all kept pages): " + ", ".join(f"{k}={v}" for k, v in df.gender.value_counts().items()))
    for scope, s in (("MAIN (physics/chemistry)", df[df.main_field]), ("BIOLOGY (robustness)", df[~df.main_field])):
        note(f"\n{scope}: pages", len(s))
        note("  matched to OpenAlex by ID", int(s.matched.sum()))
        note("  dropped as doubtful match (name similarity < 0.6)", int(s.match_doubtful.sum()))
        note("  usable for comparisons (matched, not doubtful, gender m/f, citations > 0)", int(s.usable.sum()))
        for g in ("female", "male"):
            gs = s[s.gender == g]
            note(f"    {g}: {int(gs.usable.sum())} usable of {len(gs)} pages "
                 f"({gs.usable.mean():.1%}); split OpenAlex profiles among matched: "
                 f"{(gs[gs.matched].n_profiles > 1).mean():.1%}; doubtful: {gs.match_doubtful.mean():.1%}")

    u = df[df.usable & df.main_field]
    note("\nUsable main set, per field x decade (women / men):")
    tab = u.groupby(["field_group", "birth_decade", "gender"]).size().unstack(fill_value=0)
    note(tab.to_string())

    df.to_csv(PROC / "nodes.csv", index=False)
    keep = set(df.qid)
    e = edges[edges.source.isin(keep) & edges.target.isin(keep)]
    e.to_csv(PROC / "edges_clean.csv", index=False)
    note("\nedges between kept pages", len(e))

    # Hand-check sample: 50 women + 50 men among matched main-field people, so accuracy is reported by gender.
    m = df[df.matched & df.gender_known & df.main_field]
    sample = pd.concat([g.sample(50, random_state=SEED) for _, g in m.groupby("gender")])
    sample = sample[["qid", "title", "gender", "birth_year", "field", "match_method", "oa_name", "openalex_id",
                     "citations", "works", "h_index", "top_field", "name_similarity", "n_profiles"]]
    sample["wikipedia_url"] = "https://en.wikipedia.org/wiki/" + sample.title.str.replace(" ", "_")
    sample["openalex_url"] = "https://openalex.org/" + sample.openalex_id
    sample["correct"] = ""           # 1 = same person, 0 = wrong person
    sample["profile_complete"] = ""  # 1 = OpenAlex profile looks complete, 0 = clearly missing works (e.g. name change)
    sample["comment"] = ""
    out = PROC / "handcheck_sample.csv"
    if out.exists():
        print("  handcheck_sample.csv exists: not overwritten (may contain labels)")
    else:
        sample.to_csv(out, index=False)

    hc = pd.read_csv(out)
    if hc["correct"].notna().all() and len(hc):
        note("\nHand-check of matches (Wilson 95% CI):")
        for g, x in [("all", hc)] + list(hc.groupby("gender")):
            for col in ("correct", "profile_complete"):
                k, n = int(x[col].sum()), len(x)
                lo, hi = wilson(k, n)
                note(f"  {g:<7} {col:<17} {k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]")

    (PROC / "cleaning_report.txt").write_text("\n".join(rep) + "\n")
    log("derived", "nodes.csv after cleaning", len(df), f"usable_main={len(u)}")


if __name__ == "__main__":
    run()
