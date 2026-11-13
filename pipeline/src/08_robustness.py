"""Phase 5: robustness table for RQ1.

Repeats the main analysis under alternative choices and collects one table:
  bin count (3 / 5 / 10), shuffle seeds, impact measure (citations / h-index / works),
  without Nobel laureates, without the top 1% by impact, and the second field (biology).

Outputs: results/robustness.csv and results/robustness.md (paste into the supplement).
"""
import argparse
import importlib

import pandas as pd

from common import ROOT, log

net = importlib.import_module("06_network")
RES = ROOT / "results"

CONFIGS = [
    ("Main (citations, 5 bins)", dict()),
    ("3 impact bins", dict(bins=3)),
    ("10 impact bins", dict(bins=10)),
    ("Seed 1", dict(seed=1)),
    ("Seed 2", dict(seed=2)),
    ("Impact = h-index", dict(impact="h_index")),
    ("Impact = works", dict(impact="works")),
    ("Without Nobel laureates", dict(drop_nobel=True)),
    ("Without top 1% impact", dict(drop_top1=True)),
    ("Without Nobel and top 1%", dict(drop_nobel=True, drop_top1=True)),
    ("Biology (second field)", dict(fields="biology")),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=500)
    a = ap.parse_args(argv)
    cache, rows = {}, []
    for name, cfg in CONFIGS:
        fields = cfg.get("fields", "main")
        if fields not in cache:
            cache[fields] = net.load_graph(fields)
        out, _ = net.run_rq1(runs=a.runs, nodes_G=cache[fields], **cfg)
        for col, s in out["shuffle"].items():
            r = out["regression"][col]
            rows.append({"variant": name, "outcome": col, "n": s["n"], "women": s["women"],
                         "shuffle_ratio": s["gap_ratio"], "z": s["z"], "p": s["p"],
                         "reg_ratio": r["ratio"], "reg_lo": r["ratio_ci95"][0], "reg_hi": r["ratio_ci95"][1],
                         "reg_ratio_with_prizes": out["regression_with_prizes"][col]["ratio"]})
        print(f"done: {name}")
    df = pd.DataFrame(rows)
    df.to_csv(RES / "robustness.csv", index=False)

    lines = ["| Variant | Outcome | n (women) | Shuffle ratio (z) | Regression ratio [95% CI] | + prizes |",
             "|---|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.variant} | {r.outcome} | {r.n} ({r.women}) | {r.shuffle_ratio:.2f} ({r.z:+.1f}) | "
                     f"{r.reg_ratio:.2f} [{r.reg_lo:.2f}, {r.reg_hi:.2f}] | {r.reg_ratio_with_prizes:.2f} |")
    lines.append("\nRatio = women's outcome as a multiple of comparable men's (geometric means); < 1 = less visible.")
    (RES / "robustness.md").write_text("\n".join(lines) + "\n")
    log("analysis", "robustness table", len(df))
    print(pd.pivot_table(df, index="variant", columns="outcome", values="reg_ratio").round(2).to_string())


if __name__ == "__main__":
    main()
