"""Phase 4: text analysis (RQ2).

Steps
 1. Mask:  spaCy NER replaces PERSON names with NAME; pronouns -> PRON; gender words (woman, male, Mrs...)
           -> GENDERWORD; kinship words made gender-neutral (husband/wife -> spouse, son/daughter -> child,
           mother/father -> parent, brother/sister -> sibling). Cached in data/processed/text_masked/.
           Raw counts of explicit gender mentions ("first woman", "female physicist") are kept separately.
 2. Word lists: share of sentences with personal-life vs. professional words, per page.
    Regression: share ~ female + log citations + field + birth decade + deceased + log words (HC3, 95% CI).
 3. Fightin' Words (Monroe, Colaresi & Quinn 2008): weighted log-odds with an informative Dirichlet prior,
    on document frequencies (a page counts once per word, so one long page cannot dominate).
    Consistency check: z-scores recomputed within citation terciles.
 4. Hand labelling: stratified sample per gender (personal-flagged / professional-flagged / neither).
    `python 07_text.py --validate` reads the labels and reports weighted precision & recall with bootstrap CIs.
Outputs: results/rq2_text.json, results/fightin_words.csv, results/sentences_to_label.csv, figures/fig2_text.png
"""
import argparse
import json
import re
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from tqdm import tqdm

from common import PROC, ROOT, log

RES, FIG = ROOT / "results", ROOT / "figures"
MASKED = PROC / "text_masked"
MASKED.mkdir(exist_ok=True)
COL = {"female": "#C2410C", "male": "#1D4ED8"}
SEED = 2805

PRONOUNS = r"she|he|her|hers|herself|him|his|himself"
GENDER_WORDS = (r"woman|women|man|men|female|females|male|males|girl|girls|boy|boys|lady|ladies|gentleman|"
                r"gentlemen|chairwoman|chairman|spokeswoman|spokesman|businesswoman|businessman|"
                r"sportswoman|sportsman|congresswoman|congressman")
TITLES = r"\b(Mrs|Mr|Ms|Miss|Madame|Mme|Mlle|Sir|Dame|Lady|Lord)\b\.?"  # case-sensitive: avoids MS (degree)
KIN = {"husband": "spouse", "wife": "spouse", "husbands": "spouses", "wives": "spouses",
       "son": "child", "daughter": "child", "sons": "children", "daughters": "children",
       "mother": "parent", "father": "parent", "mothers": "parents", "fathers": "parents",
       "brother": "sibling", "sister": "sibling", "brothers": "siblings", "sisters": "siblings",
       "grandmother": "grandparent", "grandfather": "grandparent", "niece": "nibling", "nephew": "nibling",
       "widow": "widowed", "widower": "widowed", "fiancee": "fiance", "fiancée": "fiance",
       "motherhood": "parenthood", "fatherhood": "parenthood", "maternity": "parental", "paternity": "parental",
       "stepson": "stepchild", "stepdaughter": "stepchild", "stepmother": "stepparent", "stepfather": "stepparent"}

PERSONAL = set("""married marry marriage marriages spouse spouses divorced divorce divorces widowed remarried
child children childless parent parents grandparent grandchildren sibling siblings family families pregnant
pregnancy parenthood parental childcare raised wedding fiance stepchild stepparent nibling""".split())
PROFESSIONAL = set("""research researched researcher discovered discovery discoveries theory theories theoretical
experiment experiments experimental published publication publications professor laboratory laboratories
developed invented invention award awarded prize medal fellow elected director founded patent patents
synthesis synthesized measured proposed pioneered pioneering led thesis dissertation doctorate phd postdoctoral
lecturer faculty department institute appointed collaborated collaboration journal papers""".split())
EXPLICIT = re.compile(r"\b(first|only)\s+(woman|women|female|man|male)\b|\b(woman|female|male)\s+"
                      r"(physicist|chemist|scientist|professor|researcher)s?\b", re.I)


# ---------------------------------------------------------------- 1. masking
def mask_all(qids):
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "attribute_ruler"])
    nlp.add_pipe("sentencizer")
    nlp.max_length = 3_000_000
    todo = [q for q in qids if not (MASKED / f"{q}.txt").exists()]
    pron = re.compile(rf"\b({PRONOUNS})\b", re.I)
    gend = re.compile(rf"\b({GENDER_WORDS})\b", re.I)
    kin = re.compile(r"\b(" + "|".join(sorted(KIN, key=len, reverse=True)) + r")\b", re.I)
    texts = ((PROC / "text" / f"{q}.txt").read_text() for q in todo)
    for q, doc in tqdm(zip(todo, nlp.pipe(texts, batch_size=32)), total=len(todo), desc="mask", mininterval=20):
        sents = []
        for s in doc.sents:
            t, last = [], s.start_char
            for e in (e for e in doc.ents if e.label_ == "PERSON" and s.start_char <= e.start_char < s.end_char):
                t += [doc.text[last:e.start_char], "NAME"]
                last = e.end_char
            t.append(doc.text[last:s.end_char])
            x = "".join(t).replace("\n", " ").strip()
            x = pron.sub("PRON", x)
            x = gend.sub("GENDERWORD", x)
            x = re.sub(TITLES, "GENDERWORD", x)
            x = kin.sub(lambda m: KIN[m.group(1).lower()], x)
            if len(x.split()) >= 4:
                sents.append(x)
        (MASKED / f"{q}.txt").write_text("\n".join(sents))


GENDERED_ORGS = re.compile(
    r"L['’]?Or[ée]al[- ]?UNESCO|UNESCO[- ]L['’]?Or[ée]al|For GENDERWORD in Science|For Women in Science|"
    r"Association for (GENDERWORD|Women) in Science|(GENDERWORD|Women) in (Science|Physics|Chemistry|Engineering)|"
    r"Society of (GENDERWORD|Women) Engineers|(GENDERWORD|Women) Chemists Committee|Garvan[–-]Olin|"
    r"Maria Goeppert[- ]Mayer Award|Sigma Delta Epsilon|Mary Shepard B\. Upson|Agnes Fay Morgan|"
    r"Iota Sigma Pi|Committee on the Status of (GENDERWORD|Women) in Physics|CSWP|Emmy Noether Fellowship",
    re.I)


def unmask_safe(s):
    """Replace names of women-only awards/organisations, which would reveal gender, with ORGNAME."""
    return GENDERED_ORGS.sub("ORGNAME", s)


def tokens(s):
    return [w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in {"name", "pron", "genderword", "orgname"}]


# ---------------------------------------------------------------- 3. fightin' words
def fightin_words(docs_a, docs_b, min_docs=20, a0=10.0):
    """Log-odds with an informative prior (Monroe, Colaresi & Quinn 2008), adapted to document frequencies:
    for each word, the share of pages using it in group A vs. B (binomial), with a Beta prior centred on the
    pooled share and worth `a0` pseudo-pages. Shrinks rare words; a word every page uses scores ~0."""
    ca = Counter(w for d in docs_a for w in d)
    cb = Counter(w for d in docs_b for w in d)
    Na, Nb = len(docs_a), len(docs_b)
    vocab = [w for w in set(ca) | set(cb) if ca[w] + cb[w] >= min_docs]
    ya, yb = np.array([ca[w] for w in vocab], float), np.array([cb[w] for w in vocab], float)
    pi = (ya + yb) / (Na + Nb)
    al, be = a0 * pi + 0.5, a0 * (1 - pi) + 0.5  # +0.5 (Jeffreys) keeps words on every page finite
    la = np.log((ya + al) / (Na - ya + be))
    lb = np.log((yb + al) / (Nb - yb + be))
    var = 1 / (ya + al) + 1 / (Na - ya + be) + 1 / (yb + al) + 1 / (Nb - yb + be)
    delta = la - lb
    return pd.DataFrame({"word": vocab, "docs_women": ya, "docs_men": yb, "share_women": ya / Na,
                         "share_men": yb / Nb, "delta": delta, "z": delta / np.sqrt(var)}).sort_values("z")


# ---------------------------------------------------------------- 4. labelling
def label_sample(d, sents):
    rng = np.random.default_rng(SEED)
    rows = []
    for g in ("female", "male"):
        pool = [(q, i, s) for q in d.index[d.gender == g] for i, s in enumerate(sents[q])]
        strat = {"personal_flag": [], "professional_flag": [], "neither": []}
        for q, i, s in pool:
            t = set(tokens(s))
            k = "personal_flag" if t & PERSONAL else ("professional_flag" if t & PROFESSIONAL else "neither")
            strat[k].append((q, i, s))
        for k, xs in strat.items():
            for j in rng.choice(len(xs), min(50, len(xs)), replace=False):
                q, i, s = xs[j]
                rows.append({"qid": q, "sent_idx": i, "gender": g, "stratum": k, "stratum_pop": len(xs),
                             "sentence": s, "is_personal": "", "is_professional": ""})
    df = pd.DataFrame(rows).sample(frac=1, random_state=SEED)  # shuffle so labellers don't see strata in order
    return df


def validate(L, B=1000):
    """Weighted precision/recall for each list; strata weights = population / sample size."""
    rng = np.random.default_rng(SEED)
    out = {}
    for lst, flag_strata, col in (("personal", {"personal_flag"}, "is_personal"),
                                  ("professional", {"professional_flag"}, "is_professional")):
        def est(df):
            w = df.stratum_pop / df.groupby(["gender", "stratum"]).stratum.transform("size")
            pos = df[col].astype(int)
            flagged = df.stratum.isin(flag_strata)
            if lst == "professional":  # personal-flagged sentences also contain professional words sometimes
                flagged = flagged | df.sentence.map(lambda s: bool(set(tokens(s)) & PROFESSIONAL))
            tp = (w * pos * flagged).sum()
            return tp / max((w * flagged).sum(), 1e-9), tp / max((w * pos).sum(), 1e-9)
        p, r = est(L)
        groups = [idx.to_numpy() for idx in L.groupby(["gender", "stratum"]).groups.values()]

        def resample():  # bootstrap within each gender x stratum cell
            return L.loc[np.concatenate([rng.choice(g, len(g), replace=True) for g in groups])]
        boots = np.array([est(resample()) for _ in range(B)])
        out[lst] = {"precision": p, "precision_ci95": np.percentile(boots[:, 0], [2.5, 97.5]).tolist(),
                    "recall": r, "recall_ci95": np.percentile(boots[:, 1], [2.5, 97.5]).tolist(),
                    "n_labelled": len(L)}
        for g in ("female", "male"):
            pg, rg = est(L[L.gender == g])
            out[lst][f"precision_{g}"], out[lst][f"recall_{g}"] = pg, rg
    return out


# ---------------------------------------------------------------- figure 2
def fig2(fw, tab, ci, n_label=14):
    """(a) Scattertext-style plot (Kessler 2017): each word placed by how often it appears on men's pages (x)
    and women's pages (y), as dense frequency ranks scaled to 0-1. Words on the diagonal are used equally;
    the top-left corner is characteristic of women's pages, the bottom-right of men's.
    Colour = Fightin' Words z-score. (b) personal-life sentence share by citation quintile."""
    from adjustText import adjust_text
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

    f = fw.copy()
    f["x"] = f.share_men.rank(method="dense") / f.share_men.rank(method="dense").max()
    f["y"] = f.share_women.rank(method="dense") / f.share_women.rank(method="dense").max()
    cmap = LinearSegmentedColormap.from_list("mf", [COL["male"], "#E5E7EB", COL["female"]])
    lim = np.percentile(np.abs(f.z), 99.5)
    fig, (a, b) = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.15, 1]})
    a.scatter(f.x, f.y, c=f.z, cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim), s=6, lw=0, alpha=0.8)
    a.plot([0, 1], [0, 1], color="#9CA3AF", lw=0.8, ls=":")
    lab = pd.concat([f.nlargest(n_label, "z"), f.nsmallest(n_label, "z")])
    texts = [a.text(r.x, r.y, r.word, fontsize=8, color=COL["female"] if r.z > 0 else COL["male"],
                    fontweight="bold") for r in lab.itertuples()]
    adjust_text(texts, ax=a, arrowprops=dict(arrowstyle="-", color="#9CA3AF", lw=0.5),
                expand=(1.3, 1.6), force_text=(0.4, 0.6))
    a.text(0.02, 0.98, "more typical of\nwomen's pages", transform=a.transAxes, va="top", fontsize=9,
           color=COL["female"])
    a.text(0.98, 0.02, "more typical of\nmen's pages", transform=a.transAxes, ha="right", fontsize=9,
           color=COL["male"])
    a.set_xlabel("Frequency on men's pages (rank, low → high)")
    a.set_ylabel("Frequency on women's pages (rank, low → high)")
    a.set_xlim(-0.02, 1.02)
    a.set_ylim(-0.02, 1.02)
    a.set_title("Words on women's vs. men's pages (names, pronouns, gender words masked)",
                fontsize=10, loc="left")
    a.spines[["top", "right"]].set_visible(False)

    xs = np.arange(tab.shape[0])
    for i, g in enumerate(("male", "female")):
        m = tab[g].to_numpy()
        lo, hi = ci[g][:, 0], ci[g][:, 1]
        b.bar(xs + (i - .5) * .38, m, .38, color=COL[g], label="Women" if g == "female" else "Men",
              yerr=[m - lo, hi - m], capsize=2, error_kw={"lw": .8})
    b.set_xticks(xs, [f"Q{i + 1}" for i in xs])
    b.set_xlabel("Citation quintile (low → high)")
    b.set_ylabel("Share of sentences with personal-life words")
    b.set_title("Personal-life sentences, by impact", fontsize=10, loc="left")
    b.legend(frameon=False)
    b.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_text.png", dpi=200)
    plt.close(fig)


def scattertext_html(d, sents):
    """Interactive Scattertext explorer (supplement), on masked text."""
    import scattertext as st
    df = pd.DataFrame({"gender": np.where(d.female == 1, "Women", "Men"),
                       "text": [" ".join(" ".join(tokens(s)) for s in sents[q]) for q in d.index],
                       "title": d.title.to_numpy()})
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    corpus = (st.CorpusFromPandas(df, category_col="gender", text_col="text",
                                  nlp=st.whitespace_nlp_with_sentences).build()
              .get_unigram_corpus().remove_terms(list(ENGLISH_STOP_WORDS), ignore_absences=True))
    html = st.produce_scattertext_explorer(corpus, category="Women", category_name="Women's pages",
                                           not_category_name="Men's pages", minimum_term_frequency=20,
                                           metadata=df.title, width_in_pixels=1000)
    (RES / "fig2_scattertext.html").write_text(html)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="read hand labels and report precision/recall")
    ap.add_argument("--fields", default="main")
    a = ap.parse_args(argv)

    nodes = pd.read_csv(PROC / "nodes.csv").set_index("qid")
    d = nodes[nodes.usable & (nodes.main_field if a.fields == "main" else nodes.field_group == a.fields)].copy()
    mask_all(list(d.index))
    sents = {q: [unmask_safe(s) for s in (MASKED / f"{q}.txt").read_text().split("\n") if s] for q in d.index}

    # 2. word-list shares + explicit gender mentions
    rows = []
    for q in d.index:
        ss = sents[q]
        n = max(len(ss), 1)
        raw = (PROC / "text" / f"{q}.txt").read_text()
        rows.append({"qid": q, "n_sent": len(ss),
                     "share_personal": sum(bool(set(tokens(s)) & PERSONAL) for s in ss) / n,
                     "share_professional": sum(bool(set(tokens(s)) & PROFESSIONAL) for s in ss) / n,
                     "explicit_gender_mention": int(bool(EXPLICIT.search(raw)))})
    d = d.join(pd.DataFrame(rows).set_index("qid"))
    d["female"] = (d.gender == "female").astype(int)
    d["log_impact"] = np.log10(d.citations)
    d["log_words"] = np.log10(d.n_words)
    d["deceased"] = d.deceased.fillna(0)
    d["cit_q"] = pd.qcut(d.log_impact.rank(method="first"), 5, labels=False)
    d[["gender", "cit_q", "share_personal", "share_professional", "explicit_gender_mention", "n_sent"]].to_csv(
        RES / "rq2_page_scores.csv")

    out = {"n_pages": len(d), "women": int(d.female.sum()), "regression": {}}
    for y in ("share_personal", "share_professional", "explicit_gender_mention"):
        m = smf.ols(f"{y} ~ female + log_impact + C(field_group) + C(birth_decade) + deceased + log_words",
                    data=d).fit(cov_type="HC3")
        lo, hi = m.conf_int().loc["female"]
        out["regression"][y] = {"coef_female": m.params["female"], "ci95": [lo, hi], "p": m.pvalues["female"],
                                "mean_men": d.loc[d.female == 0, y].mean(), "mean_women": d.loc[d.female == 1, y].mean()}

    # per-quintile means with bootstrap CIs (Figure 2b)
    rng = np.random.default_rng(SEED)
    tab = d.groupby(["cit_q", "gender"]).share_personal.mean().unstack()
    ci = {g: np.array([np.percentile([rng.choice(v, len(v)).mean() for _ in range(1000)], [2.5, 97.5])
                       for v in (d[(d.cit_q == k) & (d.gender == g)].share_personal.to_numpy() for k in tab.index)])
          for g in ("female", "male")}
    out["share_personal_by_quintile"] = tab.round(4).to_dict()

    # 3. fightin' words (whole set + within citation terciles)
    docs = {q: set(w for s in sents[q] for w in tokens(s)) for q in d.index}
    fw = fightin_words([docs[q] for q in d.index[d.female == 1]], [docs[q] for q in d.index[d.female == 0]])
    d["cit_t"] = pd.qcut(d.log_impact.rank(method="first"), 3, labels=False)
    for t in range(3):
        s = d[d.cit_t == t]
        ft = fightin_words([docs[q] for q in s.index[s.female == 1]], [docs[q] for q in s.index[s.female == 0]],
                           min_docs=10).set_index("word").z
        fw[f"z_tercile{t + 1}"] = fw.word.map(ft)
    for fld in ("physics", "chemistry"):
        s_ = d[d.field_group == fld]
        ff = fightin_words([docs[q] for q in s_.index[s_.female == 1]], [docs[q] for q in s_.index[s_.female == 0]],
                           min_docs=10).set_index("word").z
        fw[f"z_{fld}"] = fw.word.map(ff)
    fw.to_csv(RES / "fightin_words.csv", index=False)
    top = pd.concat([fw.head(30), fw.tail(30)])
    both = fw.dropna(subset=["z_physics", "z_chemistry"])
    out["fightin_words_within_field"] = {
        "top60_same_sign_in_both_fields": float(np.mean(
            [np.sign(r.z_physics) == np.sign(r.z) == np.sign(r.z_chemistry) for _, r in
             pd.concat([both.head(30), both.tail(30)]).iterrows()])),
        "physics_top_women": fw.sort_values("z_physics").dropna(subset=["z_physics"]).tail(15).word.tolist()[::-1],
        "physics_top_men": fw.sort_values("z_physics").dropna(subset=["z_physics"]).head(15).word.tolist(),
        "chemistry_top_women": fw.sort_values("z_chemistry").dropna(subset=["z_chemistry"]).tail(15).word.tolist()[::-1],
        "chemistry_top_men": fw.sort_values("z_chemistry").dropna(subset=["z_chemistry"]).head(15).word.tolist()}
    out["fightin_words"] = {
        "top_women": fw.tail(25).word.tolist()[::-1], "top_men": fw.head(25).word.tolist(),
        "top60_same_sign_in_all_terciles": float(np.mean(
            [np.all(np.sign(r[[f"z_tercile{t}" for t in (1, 2, 3)]].astype(float)) == np.sign(r.z))
             for _, r in top.iterrows()]))}

    fig2(fw, tab, ci)
    scattertext_html(d, sents)

    # 4. hand labelling
    lab = RES / "sentences_to_label.csv"
    if not lab.exists():
        label_sample(d, sents).to_csv(lab, index=False)
        print(f"Wrote {lab}: fill is_personal and is_professional (1/0), then rerun with --validate")
    if a.validate:
        L = pd.read_csv(lab).dropna(subset=["is_personal", "is_professional"])
        out["validation"] = validate(L)

    (RES / "rq2_text.json").write_text(json.dumps(out, indent=2, default=float))
    log("analysis", "RQ2 text analysis", len(d))
    r = out["regression"]
    print(f"\nPages: {len(d)} ({out['women']} women)")
    for y, v in r.items():
        print(f"{y:<26} women {v['mean_women']:.4f} vs men {v['mean_men']:.4f} | adjusted diff "
              f"{v['coef_female']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] p={v['p']:.3g}")
    print("Top women's-page words:", ", ".join(out["fightin_words"]["top_women"][:15]))
    print("Top men's-page words:  ", ", ".join(out["fightin_words"]["top_men"][:15]))
    w = out["fightin_words_within_field"]
    print(f"Within field, top-60 same sign in physics and chemistry: {w['top60_same_sign_in_both_fields']:.0%}")
    for k in ("physics_top_women", "physics_top_men", "chemistry_top_women", "chemistry_top_men"):
        print(f"  {k:<22}", ", ".join(w[k][:12]))
    print(f"Top-60 words same sign in all citation terciles: {out['fightin_words']['top60_same_sign_in_all_terciles']:.0%}")


if __name__ == "__main__":
    main()
