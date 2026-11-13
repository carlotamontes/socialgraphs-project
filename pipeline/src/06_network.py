"""Phase 3: network analysis (RQ1, RQ3) with null models.

RQ1  Visibility at equal impact. Outcomes: PageRank, in-degree (within the scientist network), pageviews
     (12 months), in-links from all of English Wikipedia, page length.
     (a) Shuffle test: gender labels permuted within strata = field x birth decade x impact bin.
         Statistic = within-stratum gap (mean log outcome, women - men), weighted by number of women.
     (b) Regression: log outcome ~ female + log impact + field + birth decade + deceased (HC3 SEs, 95% CI);
         second model adds Nobel + log(1 + awards) to see how much of the gap runs through prizes.
RQ3  One quantity: share of in-links to women's pages that come from women's pages, vs. a null that shuffles
     gender within field x decade (network fixed). Louvain communities are descriptive only (Figure 3).

Usage examples:
  python 06_network.py                         # main analysis + Figures 1 and 3
  python 06_network.py --impact h_index --skip-rq3
  python 06_network.py --drop-nobel --drop-top1 --skip-rq3
  python 06_network.py --fields biology        # robustness field
"""
import argparse
import json

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.metrics import normalized_mutual_info_score

from common import PROC, ROOT, log

RES, FIG = ROOT / "results", ROOT / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
COL = {"female": "#C2410C", "male": "#1D4ED8", "other": "#9CA3AF"}
OUTCOMES = {  # column -> (transformed column, label)
    "pagerank": ("log_pr", "PageRank (log$_{10}$)"),
    "in_degree": ("log_indeg", "In-degree within network (log$_{10}$ 1+x)"),
    "pageviews_60d": ("log_views", "Pageviews, last 60 days (log$_{10}$ 1+x)"),
    "backlinks_enwiki": ("log_backlinks", "In-links from all of Wikipedia (log$_{10}$ 1+x)"),
    "n_words": ("log_words", "Page length, words (log$_{10}$)"),
}
IMPACT_LABEL = {"citations": "Citations", "h_index": "h-index", "works": "Works"}


# ---------------------------------------------------------------- data
def load_graph(fields):
    nodes = pd.read_csv(PROC / "nodes.csv")
    nodes = nodes[nodes.main_field] if fields == "main" else nodes[nodes.field_group == fields]
    edges = pd.read_csv(PROC / "edges_clean.csv")
    G = nx.DiGraph()
    G.add_nodes_from(nodes.qid)
    G.add_edges_from(edges[edges.source.isin(G) & edges.target.isin(G)].itertuples(index=False))
    nodes = nodes.set_index("qid")
    nodes["in_degree"] = pd.Series(dict(G.in_degree()))
    nodes["out_degree"] = pd.Series(dict(G.out_degree()))
    nodes["pagerank"] = pd.Series(nx.pagerank(G, alpha=0.85))
    return nodes, G


def comparison_set(nodes, impact="citations", bins=5, drop_nobel=False, drop_top1=False):
    d = nodes[nodes.usable & (nodes[impact] > 0)].copy()
    notes = {"start": len(d)}
    if drop_nobel:
        d = d[d.nobel.fillna(0) == 0]
        notes["after_drop_nobel"] = len(d)
    if drop_top1:
        d = d[d[impact] < d[impact].quantile(0.99)]
        notes["after_drop_top1pct"] = len(d)
    d["female"] = (d.gender == "female").astype(int)
    d["log_impact"] = np.log10(d[impact])
    d["impact_bin"] = pd.qcut(d.log_impact.rank(method="first"), bins, labels=False)
    d["stratum"] = d.field_group + "|" + d.birth_decade.astype(str) + "|" + d.impact_bin.astype(str)
    d["deceased"] = d.deceased.fillna(0)
    d["log_awards"] = np.log10(1 + d.n_awards.fillna(0))
    d["nobel"] = d.nobel.fillna(0)
    for col, (t, _) in OUTCOMES.items():
        if col in d and d[col].notna().any():
            d[t] = np.log10(d[col]) if col in ("pagerank", "n_words") else np.log10(1 + d[col])
    return d, notes


# ---------------------------------------------------------------- RQ1
def stratified_shuffle(d, y, runs, rng):
    """Within-stratum gender gap and its null distribution (labels shuffled within strata)."""
    s = d[[y, "female", "stratum"]].dropna()
    codes, strata = pd.factorize(s.stratum)
    yv, f = s[y].to_numpy(), s.female.to_numpy()
    k = len(strata)
    n_f = np.bincount(codes, weights=f, minlength=k)
    n_m = np.bincount(codes, minlength=k) - n_f
    ok = (n_f > 0) & (n_m > 0)  # strata with both genders
    tot = np.bincount(codes, weights=yv, minlength=k)

    def gap(fv):
        sf = np.bincount(codes, weights=yv * fv, minlength=k)
        g = sf[ok] / n_f[ok] - (tot[ok] - sf[ok]) / n_m[ok]
        return np.average(g, weights=n_f[ok])

    obs = gap(f)
    order = np.argsort(codes, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(codes, minlength=k))]
    null = np.empty(runs)
    for i in range(runs):
        fv = f[order].copy()
        for a, b in zip(bounds[:-1], bounds[1:]):
            fv[a:b] = rng.permutation(fv[a:b])
        out = np.empty_like(fv)
        out[order] = fv
        null[i] = gap(out)
    z = (obs - null.mean()) / null.std()
    p = (np.sum(np.abs(null - null.mean()) >= abs(obs - null.mean())) + 1) / (runs + 1)
    return {"n": int(len(s)), "women": int(f.sum()), "strata_used": int(ok.sum()), "strata_total": int(k),
            "women_in_used_strata": int(n_f[ok].sum()), "gap_log10": float(obs),
            "gap_ratio": float(10 ** obs),  # women's outcome as a multiple of men's (geometric mean)
            "null_mean": float(null.mean()), "null_sd": float(null.std()), "z": float(z), "p": float(p)}, null


def regression(d, y, with_prizes=False):
    f = f"{y} ~ female + log_impact + C(field_group) + C(birth_decade) + deceased"
    if with_prizes:
        f += " + nobel + log_awards"
    m = smf.ols(f, data=d.dropna(subset=[y])).fit(cov_type="HC3")
    lo, hi = m.conf_int().loc["female"]
    b = m.params["female"]
    return {"coef_female_log10": float(b), "ci95": [float(lo), float(hi)], "p": float(m.pvalues["female"]),
            "ratio": float(10 ** b), "ratio_ci95": [float(10 ** lo), float(10 ** hi)],
            "coef_log_impact": float(m.params["log_impact"]), "n": int(m.nobs), "r2": float(m.rsquared)}


def two_part(d):
    """PageRank gap split into (1) whether a page gets any in-link from another scientist's page and
    (2) PageRank among pages that do. Same covariates as the main regression."""
    d = d.assign(any_in=(d.in_degree > 0).astype(int))
    f = "~ female + log_impact + C(field_group) + C(birth_decade) + deceased"
    m1 = smf.ols("any_in " + f, data=d).fit(cov_type="HC3")
    lk = d[d.any_in == 1]
    m2 = smf.ols("log_pr " + f, data=lk).fit(cov_type="HC3")
    return {"share_any_inlink": d.groupby("gender").any_in.mean().to_dict(),
            "any_inlink_diff_female": float(m1.params["female"]),
            "any_inlink_diff_ci95": m1.conf_int().loc["female"].tolist(),
            "linked_only_pr_ratio": float(10 ** m2.params["female"]),
            "linked_only_pr_ratio_ci95": (10 ** m2.conf_int().loc["female"]).tolist(),
            "linked_only_n": int(len(lk)), "linked_only_women": int(lk.female.sum())}


def fig1(d, out, nulls, impact, tag):
    """(a) citations vs PageRank by gender, binned means with 95% CI, pages without in-links as a strip;
    (b) observed gap vs. stratified-shuffle null for every visibility outcome."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw={"width_ratios": [1.7, 1]})
    linked = d.in_degree > 0
    floor = d.log_pr.min()
    rng = np.random.default_rng(0)
    for g in ("male", "female"):
        s = d[(d.gender == g) & linked]
        a.scatter(s.log_impact, s.log_pr, s=7, alpha=0.35, color=COL[g], lw=0)
        z = d[(d.gender == g) & ~linked]
        a.scatter(z.log_impact, floor - 0.25 + rng.uniform(-.08, .08, len(z)) + (0.1 if g == "female" else -0.1),
                  s=4, alpha=0.25, color=COL[g], lw=0)
    edges = np.quantile(d.log_impact, np.linspace(0, 1, 9))
    d = d.assign(xb=np.clip(np.digitize(d.log_impact, edges[1:-1]), 0, 7))
    for g, lab in (("male", "Men"), ("female", "Women")):
        s = d[d.gender == g].groupby("xb")
        m, se, x = s.log_pr.mean(), s.log_pr.sem(), s.log_impact.median()
        a.plot(x, m, color=COL[g], lw=2.6, marker="o", ms=4,
               label=f"{lab} (n={int((d.gender == g).sum()):,}), mean by citation octile")
        a.fill_between(x, m - 1.96 * se, m + 1.96 * se, color=COL[g], alpha=0.18, lw=0)
    a.axhline(floor - 0.12, color="#E5E7EB", lw=0.8)
    a.text(d.log_impact.min(), floor - 0.25, "no in-links from\nother scientists' pages", fontsize=7.5,
           color="#6B7280", va="center", ha="left")
    tp = out["two_part"]["share_any_inlink"]
    a.set_title(f"Pages with ≥1 in-link: women {tp['female']:.0%}, men {tp['male']:.0%}", fontsize=9.5, loc="left")
    a.set_xlabel(f"{IMPACT_LABEL[impact]} (log$_{{10}}$, OpenAlex)")
    a.set_ylabel("PageRank in scientist network (log$_{10}$)")
    a.legend(loc="upper left", frameon=False, fontsize=8.5)
    a.spines[["top", "right"]].set_visible(False)

    names = {"log_pr": "PageRank", "log_indeg": "In-degree", "log_views": "Pageviews (60 d)",
             "log_backlinks": "In-links, all Wikipedia", "log_words": "Page length"}
    keys = [k for k in names if k in nulls]
    col_of = {v[0]: k for k, v in OUTCOMES.items()}
    for i, k in enumerate(keys):
        nl = 10 ** nulls[k]
        lo, hi = np.percentile(nl, [2.5, 97.5])
        b.plot([lo, hi], [i, i], color="#D1D5DB", lw=9, solid_capstyle="butt")
        sh = out["shuffle"][col_of[k]]
        b.plot(sh["gap_ratio"], i, "o", color=COL["female"], ms=8)
        b.text(max(hi, sh["gap_ratio"]) + 0.012, i, f"z = {sh['z']:.1f}", va="center", fontsize=8, color="#374151")
    b.axvline(1, color="#9CA3AF", lw=0.8, ls=":")
    b.set_yticks(range(len(keys)), [names[k] for k in keys])
    b.invert_yaxis()
    b.set_xlabel("Women / comparable men (within field × decade × impact)")
    b.set_title("Observed (dot) vs. 95% of shuffled-gender nulls (bar)", fontsize=9.5, loc="left")
    b.spines[["top", "right", "left"]].set_visible(False)
    b.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig(FIG / f"fig1_{tag}.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- RQ3
def inlink_share_from_women(nodes, G, rng, runs=1000):
    known = nodes[nodes.gender_known]
    idx = {q: i for i, q in enumerate(known.index)}
    E = np.array([(idx[u], idx[v]) for u, v in G.edges() if u in idx and v in idx])
    fem = (known.gender == "female").to_numpy().astype(int)

    def stat(fv):
        to_w = fv[E[:, 1]] == 1
        to_m = ~to_w
        return fv[E[to_w, 0]].mean(), fv[E[to_m, 0]].mean()

    obs_w, obs_m = stat(fem)
    groups = [np.where(g)[0] for g in
              (known.field_group + "|" + known.birth_decade.astype(str)).pipe(
                  lambda s: [s.to_numpy() == v for v in s.unique()])]
    nw, nm = np.empty(runs), np.empty(runs)
    for i in range(runs):
        fv = fem.copy()
        for g in groups:
            fv[g] = rng.permutation(fv[g])
        nw[i], nm[i] = stat(fv)
    return {"edges_between_gender_known": int(len(E)),
            "share_women_among_linking_pages_overall": float(fem[E[:, 0]].mean()),
            "to_women": {"observed": float(obs_w), "null_mean": float(nw.mean()), "null_sd": float(nw.std()),
                         "z": float((obs_w - nw.mean()) / nw.std())},
            "to_men": {"observed": float(obs_m), "null_mean": float(nm.mean()), "null_sd": float(nm.std()),
                       "z": float((obs_m - nm.mean()) / nm.std())},
            "null": "gender shuffled within field x birth decade, network fixed"}


def communities(nodes, G, rng, seeds=10):
    U = G.to_undirected()
    U = U.subgraph(max(nx.connected_components(U), key=len)).copy()
    parts = [nx.community.louvain_communities(U, seed=s) for s in range(seeds)]
    order = list(U)
    lab = [[{n: i for i, c in enumerate(p) for n in c}[n] for n in order] for p in parts]
    nmi = [normalized_mutual_info_score(lab[0], l) for l in lab[1:]]
    Q = nx.community.modularity(U, parts[0])
    Qn = []
    for _ in range(5):
        R = nx.Graph(nx.configuration_model([k for _, k in U.degree()], seed=int(rng.integers(1e9))))
        R.remove_edges_from(nx.selfloop_edges(R))
        Qn.append(nx.community.modularity(R, nx.community.louvain_communities(R, seed=0)))
    # Within-community PageRank percentile, women vs men, for every seed (stability check).
    seed_stats = []
    for sd, p in enumerate(parts):
        cm = {n: i for i, c in enumerate(sorted(p, key=len, reverse=True)) for n in c}
        t = nodes.loc[order].assign(community=pd.Series(cm))
        t = t[t.gender_known]
        t["pct"] = t.groupby("community").pagerank.rank(pct=True)
        big = t.community.value_counts().pipe(lambda v: v[v >= 100].index)
        per = t[t.community.isin(big)].groupby(["community", "gender"]).pct.mean().unstack()
        seed_stats.append({"seed": sd, "mean_pct_women": float(t[t.gender == "female"].pct.mean()),
                           "mean_pct_men": float(t[t.gender == "male"].pct.mean()),
                           "communities_ge100": int(len(per)),
                           "communities_women_lower": int((per.female < per.male).sum())})
    comm = {n: i for i, c in enumerate(sorted(parts[0], key=len, reverse=True)) for n in c}
    cc = nodes.loc[order].assign(community=pd.Series(comm))
    cc["pct_in_comm"] = cc[cc.gender_known].groupby("community").pagerank.rank(pct=True)
    k = cc[cc.gender_known]
    tab = k.groupby("community").agg(
        size=("gender", "size"), share_women=("gender", lambda s: (s == "female").mean()),
        share_physics=("field_group", lambda s: (s == "physics").mean()),
        median_birth=("birth_year", "median"),
        hub=("pagerank", lambda s: cc.loc[s.idxmax(), "title"]))
    return {"lcc_nodes": U.number_of_nodes(), "n_communities": len(parts[0]), "modularity": Q,
            "modularity_config_null_mean": float(np.mean(Qn)), "nmi_vs_seed0_mean": float(np.mean(nmi)),
            "nmi_vs_seed0_min": float(np.min(nmi)), "within_community_rank_by_seed": seed_stats,
            "communities_ge_30": tab[tab["size"] >= 30].round(3).reset_index().to_dict("records")}, cc


def fig3(G, cc, tag, n_comm=9):
    """(a) the nine largest Louvain communities, each laid out separately on a 3x3 grid; colour = gender,
    size = citations; label = most central page + share of women.
    (b) mean within-community PageRank percentile of women vs. men, per community."""
    top = list(cc.community.value_counts().index[:n_comm])
    U = G.to_undirected()
    fig = plt.figure(figsize=(15, 9.5))
    a = fig.add_axes([0.0, 0.03, 0.64, 0.92])
    b = fig.add_axes([0.73, 0.12, 0.25, 0.76])
    cit_all = np.log10(cc.citations.fillna(0) + 1)
    names = []
    for i, k in enumerate(top):
        members = cc.index[cc.community == k]
        H = U.subgraph(members)
        pos = nx.spring_layout(H, k=1.2 / np.sqrt(len(H)), iterations=80, seed=1)
        off = np.array([i % 3, -(i // 3)]) * 2.6
        pos = {n: p + off for n, p in pos.items()}
        nx.draw_networkx_edges(H, pos, ax=a, alpha=0.05, width=0.3)
        for g in ("male", "other", "female"):
            ns = [n for n in H if (cc.loc[n, "gender"] if cc.loc[n, "gender"] in COL else "other") == g]
            nx.draw_networkx_nodes(H, pos, nodelist=ns, ax=a, node_color=COL[g], alpha=0.85, linewidths=0,
                                   node_size=[3 + 55 * (cit_all[n] / cit_all.max()) ** 2 for n in ns])
        sub = cc.loc[members]
        known = sub[sub.gender_known]
        hub = sub.pagerank.idxmax()
        names.append(sub.loc[hub, "title"])
        a.text(off[0], off[1] + 1.22, f"{chr(65 + i)}. {sub.loc[hub, 'title']}\n"
               f"{(known.gender == 'female').mean():.0%} women · n={len(sub)}",
               ha="center", fontsize=8.5, color="#111827")
    a.scatter([], [], color=COL["female"], label="Women", s=30)
    a.scatter([], [], color=COL["male"], label="Men", s=30)
    a.legend(loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=2, frameon=False)
    a.set_title("Nine largest link communities (Louvain) · label = most central page · size = citations",
                fontsize=10, pad=34)
    a.set_axis_off()

    k = cc[cc.gender_known & cc.community.isin(top)]
    per = k.groupby(["community", "gender"]).pct_in_comm.mean().unstack().loc[top]
    ys = np.arange(len(top))
    for y, (_, r) in zip(ys, per.iterrows()):
        b.plot([r.female, r.male], [y, y], color="#D1D5DB", lw=2, zorder=1)
    b.scatter(per.male, ys, color=COL["male"], s=40, zorder=2, label="Men")
    b.scatter(per.female, ys, color=COL["female"], s=40, zorder=2, label="Women")
    allk = cc[cc.gender_known]
    yo = len(top) + 0.6
    mw, mm = allk[allk.gender == "female"].pct_in_comm.mean(), allk[allk.gender == "male"].pct_in_comm.mean()
    b.plot([mw, mm], [yo, yo], color="#9CA3AF", lw=2.5)
    b.scatter([mm], [yo], color=COL["male"], s=60, marker="D")
    b.scatter([mw], [yo], color=COL["female"], s=60, marker="D")
    b.set_yticks(list(ys) + [yo], [f"{chr(65 + i)}. {n}" for i, n in enumerate(names)] + ["All communities"],
                 fontsize=8.5)
    b.invert_yaxis()
    b.axvline(0.5, color="#9CA3AF", lw=0.8, ls=":")
    b.set_xlim(0.2, 0.7)
    b.set_xlabel("Mean PageRank percentile within own community")
    b.set_title("Within every community, women sit\ncloser to the periphery", fontsize=10, loc="left")
    b.legend(frameon=False, loc="lower right", fontsize=8.5)
    b.spines[["top", "right", "left"]].set_visible(False)
    b.tick_params(axis="y", length=0)
    fig.savefig(FIG / f"fig3_{tag}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- main
def run_rq1(fields="main", impact="citations", bins=5, runs=1000, seed=2805, drop_nobel=False,
            drop_top1=False, nodes_G=None, figure=False):
    """Returns a dict of results. Importable by 08_robustness.py."""
    rng = np.random.default_rng(seed)
    nodes, G = nodes_G or load_graph(fields)
    d, notes = comparison_set(nodes, impact, bins, drop_nobel, drop_top1)
    tag = f"{fields}_{impact}_b{bins}_s{seed}" + ("_nonobel" if drop_nobel else "") + ("_notop1" if drop_top1 else "")
    out = {"config": dict(fields=fields, impact=impact, bins=bins, runs=runs, seed=seed,
                          drop_nobel=drop_nobel, drop_top1=drop_top1),
           "graph": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                     "isolates": nx.number_of_isolates(G),
                     "largest_wcc": len(max(nx.weakly_connected_components(G), key=len))},
           "comparison_set": {**notes, "n": len(d), "women": int(d.female.sum()), "men": int((1 - d.female).sum())},
           "shuffle": {}, "regression": {}, "regression_with_prizes": {}}
    nulls, gaps = {}, {}
    for col, (y, _) in OUTCOMES.items():
        if y not in d:
            continue
        res, null = stratified_shuffle(d, y, runs, rng)
        out["shuffle"][col], nulls[y], gaps[y] = res, null, res["gap_log10"]
        out["regression"][col] = regression(d, y)
        out["regression_with_prizes"][col] = regression(d, y, with_prizes=True)
    out["two_part"] = two_part(d)
    if figure:
        fig1(d, out, nulls, impact, tag)
    (RES / f"rq1_{tag}.json").write_text(json.dumps(out, indent=2))
    log("analysis", f"RQ1 {tag}", len(d))
    return out, (nodes, G)


def summary(out):
    print(f"\nComparison set: {out['comparison_set']}")
    print(f"{'outcome':<18}{'shuffle gap (x)':>16}{'z':>8}{'p':>8}   {'regression ratio [95% CI]':<30}{'+prizes':>10}")
    for col, s in out["shuffle"].items():
        r, rp = out["regression"][col], out["regression_with_prizes"][col]
        print(f"{col:<18}{s['gap_ratio']:>16.3f}{s['z']:>8.2f}{s['p']:>8.3f}   "
              f"{r['ratio']:.3f} [{r['ratio_ci95'][0]:.3f}, {r['ratio_ci95'][1]:.3f}]{rp['ratio']:>12.3f}")
    print("(ratios = women's outcome as a multiple of comparable men's; < 1 means less visible)")
    t = out.get("two_part")
    if t:
        print(f"Two-part: any in-link women {t['share_any_inlink'].get('female', 0):.1%} vs men "
              f"{t['share_any_inlink'].get('male', 0):.1%}; adjusted diff {t['any_inlink_diff_female']:+.3f} "
              f"[{t['any_inlink_diff_ci95'][0]:+.3f}, {t['any_inlink_diff_ci95'][1]:+.3f}]; PageRank among linked "
              f"pages ratio {t['linked_only_pr_ratio']:.3f} [{t['linked_only_pr_ratio_ci95'][0]:.3f}, "
              f"{t['linked_only_pr_ratio_ci95'][1]:.3f}]")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields", default="main", help="main | biology")
    ap.add_argument("--impact", default="citations", choices=["citations", "h_index", "works"])
    ap.add_argument("--bins", type=int, default=5)
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=2805)
    ap.add_argument("--drop-nobel", action="store_true")
    ap.add_argument("--drop-top1", action="store_true")
    ap.add_argument("--skip-rq3", action="store_true")
    a = ap.parse_args(argv)

    out, (nodes, G) = run_rq1(a.fields, a.impact, a.bins, a.runs, a.seed, a.drop_nobel, a.drop_top1, figure=True)
    nodes.to_csv(RES / f"centrality_{a.fields}.csv")
    summary(out)

    if not a.skip_rq3:
        rng = np.random.default_rng(a.seed)
        r3 = {"inlinks_from_women": inlink_share_from_women(nodes, G, rng, a.runs)}
        r3["communities"], cc = communities(nodes, G, rng)
        (RES / f"rq3_{a.fields}.json").write_text(json.dumps(r3, indent=2, default=float))
        fig3(G, cc, a.fields)
        i = r3["inlinks_from_women"]
        print(f"\nRQ3: share of in-links to women's pages from women = {i['to_women']['observed']:.3f} "
              f"(null {i['to_women']['null_mean']:.3f} ± {i['to_women']['null_sd']:.3f}, z={i['to_women']['z']:.1f}); "
              f"to men's pages = {i['to_men']['observed']:.3f} (null {i['to_men']['null_mean']:.3f})")
        c = r3["communities"]
        rs = pd.DataFrame(c["within_community_rank_by_seed"])
        print(f"Within-community PageRank percentile across {len(rs)} seeds: women {rs.mean_pct_women.mean():.3f} "
              f"vs men {rs.mean_pct_men.mean():.3f}; communities (n>=100) where women rank lower: "
              f"{rs.communities_women_lower.sum()} of {rs.communities_ge100.sum()}")
        print(f"Communities: {c['n_communities']} (LCC {c['lcc_nodes']}), Q={c['modularity']:.3f} "
              f"vs null {c['modularity_config_null_mean']:.3f}, NMI across seeds {c['nmi_vs_seed0_mean']:.2f}")


if __name__ == "__main__":
    main()
