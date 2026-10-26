---
Course: 02805 Social Graphs and Interactions (DTU, Fall 2026)
Source: https://sunelehmann.com/socialgraphs2026-web/weeks/week2.html
Textbook: Michele Coscia, The Atlas for the Aspiring Network Scientist, 2nd ed. (networkatlas.eu)
Status: full page now published (2026-09-09 session) — sections 1-8, exercises 2.1-2.11.
---

# Week 2 — Models & Null Models

Study notes: a resume of the Week 2 course page, cross-referenced with the matching textbook
chapters. Companion notebook: `../exercises/week2/2.1-2.9_models_and_null_models.ipynb`
(exercises 2.1-2.4 fully answered; 2.5a-2.9 in progress).

## 1 · Why models at all?

Network science's founding move, borrowed straight from physics: don't try to model every
detail of a complex system, find the *simplest possible mechanism* that reproduces its most
important large-scale properties. The method is iterative — build a model, compare it against
real networks, find what it gets wrong, build the next model to fix that specific gap. Week 2
walks through three successive iterations built over roughly forty years:

1. **Random graphs** (Erdős–Rényi, 1959) — the null model: no mechanism at all, just chance.
2. **Watts–Strogatz** (1998) — adds clustering without sacrificing short paths.
3. **Barabási–Albert** (1999) — adds hubs / power-law degree distributions (site §6, not yet
   published with exercises).

## 2 · The random graph — networks with (almost) no data

**Model.** Erdős and Rényi's *G(n,p)*: take *n* nodes, and for every one of the
*n(n−1)/2* possible pairs, flip a biased coin with probability *p* and add the edge if it
comes up heads.

**Why study it with no data available (and why keep it now):** (1) it's the natural
maximum-entropy null model — anything a random graph produces "for free" needs no special
explanation when it also shows up in a real network; (2) it's mathematically tractable —
exact results (the phase transition, path-length scaling) are provable by hand. Today, with
data everywhere, reason (1) is why it survives: it's the baseline every "surprising" property
of a real network gets compared against.

**Key formulas**
- Expected number of links: ⟨m⟩ = p·n(n−1)/2
- Expected average degree: ⟨k⟩ = p·(n−1)
- Degree distribution: **Poisson** with mean ⟨k⟩ (binomial in the exact derivation, Poisson in
  the large-*n* limit — Atlas §16.2) — short-tailed, essentially no nodes far from ⟨k⟩.
- Average path length: d ≈ ln n / ln⟨k⟩ (grows only logarithmically with network size).
- Clustering: CC_v = p for every node — vanishingly small for any sparse real-sized network
  (Atlas §16.5's derivation).
- P(a given node is isolated) = (1−p)^(n−1) ≈ e^(−⟨k⟩); expected number of isolates =
  n·e^(−⟨k⟩).

**The giant component / phase transition.** As ⟨k⟩ crosses **1**, the network flips from "many
small fragments" to "one component holding a finite fraction of all nodes" (Atlas §16.3–16.4
derives this exactly: `|V|(1-p)^|V| = 1` ⇒ p = ln|V|/|V|). Below ⟨k⟩=1 the largest component
grows only logarithmically with n; above it, linearly. The *last* isolated node doesn't
disappear until ⟨k⟩ grows like ln n, though — much later than the transition itself.

**Explorables referenced:** "Poisson vs. Marvel" (Marvel's real degree distribution vs. a
Poisson with the same ⟨k⟩) and "ER phase transition" (giant component emerging as ⟨k⟩ crosses 1).

**Textbook:** Atlas Ch. 16 *Random Graphs*, all sections — §16.1 building the model, §16.2
degree distribution, §16.3 connected components / giant component, §16.4 average path length,
§16.5 clustering, §16.6 summary (random graphs nail giant components and short paths; they miss
degree distribution shape, clustering, and communities — exactly why Watts–Strogatz and
Barabási–Albert exist).

## 3 · Six degrees — real networks have short paths

Milgram's 1967 experiment: strangers in Nebraska hand-delivering letters to a Boston
stockbroker through personal acquaintances only. Successful chains averaged **~6 hops** — "six
degrees of separation," the small-world property: real networks have surprisingly short
distances relative to their size. Random graphs already have this property too (path lengths
grow only as log n), which makes it, on its own, an unsurprising thing for a model to
reproduce — the real test of a model is whether it *also* gets clustering right (next section).

## 4 · Something is missing — clustering

**Local clustering coefficient** of node *i*: what fraction of *i*'s neighbors are themselves
connected to each other.

    C_i = 2·e_i / (k_i·(k_i − 1))

where e_i = number of edges actually present among node i's k_i neighbors, and
k_i(k_i−1)/2 = number of *possible* such edges (the "triads" centered on i). Ranges 0 (no
neighbors connected) to 1 (neighborhood is a complete clique). C_i is undefined (0/0) for
degree ≤ 1 — reported as 0 by convention.

**Network-level (average) clustering** C = mean of C_i over all nodes. Different from
**transitivity** (global clustering: triangles / connected triples, weighting every *triad*
equally rather than every *node* — the two coincide only in a regular graph where every node
has the same degree).

**Marvel numbers:** C ≈ 0.31 vs. transitivity ≈ 0.18; the matched random G(n,p) gives C ≈ 0.03
— roughly ten times lower. Real networks have far more triangles than chance alone predicts.

**Explorable referenced:** "Clustering counter" (interactively toggle neighbor edges, watch
C_i change).

**Textbook:** Atlas Ch. 12 §12.2 *Clustering Coefficient* (global and local definitions, worked
examples); §12.1 *Density & Real Networks* for the density context clustering builds on.

## 5 · Watts & Strogatz — perched between order and randomness

**The gap:** random graphs have short paths but ~zero clustering; a ring lattice (each node
linked to its k nearest neighbors) has high clustering but path length that grows *linearly*
with n. Neither alone matches real networks, which have both.

**The model:** start from a ring lattice, then rewire each edge to a uniformly random new
endpoint with probability *p*.

- **Insight 1 — shortcuts:** a handful of rewired edges create long-range "shortcuts" through
  the ring. A single shortcut can sit on the shortest path between many far-apart pairs at
  once, so path length collapses network-wide after only a few rewirings — while clustering,
  being a purely local, node-by-node quantity, is barely touched until a *much* larger
  fraction of edges has moved.
- **Insight 2 — a dial:** p interpolates continuously between order (p=0, lattice: high C, long
  paths) and randomness (p=1, random-graph-like: low C, short paths). Small p (≈0.01–0.05 for
  typical sizes) gives *both* high clustering *and* short paths simultaneously — the
  "small-world" regime.

**Marvel's signature:** clustering far above random expectation, path length close to random
expectation (avg. distance 2.7, diameter 6) — exactly the WS pattern.

**Explorables referenced:** "Lattice to random" (colors show distance-from-start as shortcuts
collapse paths while preserving clustering) and "WS rewiring" (systematic sweep over small p on
log axes).

**Textbook:** Atlas Ch. 17 §17.1 *Clustering* — covers the small-world family via Watts's
"cavemen" model (tight cliques/"caves" loosely connected by a few random inter-cave links —
conceptually the same shortcut mechanism as the ring-lattice rewiring, framed differently).

## 6 · The discovery of power laws

**Watts' regret:** Watts & Strogatz had the data to check whether real degree distributions
were Poisson-shaped (as their own model quietly assumes) and never did. Barabási's group did —
plotting the Web, the Internet, and citation networks on log–log axes gave straight lines, not
the curved Poisson shape. That straight line is a **power law**: P(k) ~ k^(−γ).

**Why a random graph can't produce a Spider-Man (extreme-value cutoff):** the course page
states "Spider-Man has 106 links, average 9.5; the biggest hub a corresponding random network
could produce is around 19" without showing the calculation — it's meant to be checked, not
taken on faith. The reasoning: for a random network (degree ~ Poisson(⟨k⟩)), the *expected
number* of nodes with degree ≥ k is N·P(X≥k). The plausible maximum degree k_max is where that
count drops through ~1 — above it, seeing even one such node would be a statistical surprise.
For Marvel (N=303, ⟨k⟩=9.5): N·P(X≥k) ≈ 5.4 at k=17, 2.7 at k=18, **1.3 at k=19**, 0.6 at
k=20 — the crossing sits right at 19, matching the page's figure exactly. Spider-Man's 106 is
so far into the Poisson tail (individual probability ~10⁻⁵⁸) that it's not "rare," it's a sign
the generating mechanism must be something other than chance — the empirical anomaly the BA
model below is built to explain.

**Barabási–Albert (1999) model** — two ingredients, both necessary (isolating each is the point
of Exercise 2.5b part 4 — neither one alone reproduces hubs):

1. **Growth** — the network starts small (2 nodes, 2.5b.1) and new nodes keep arriving over
   time — not a fixed *n* from the start, unlike G(n,p).
2. **Preferential attachment** — each new node connects preferentially to already well-connected
   nodes: Π(k_i) = k_i / Σ_j k_j.

**The endpoint-list trick (2.5a.1):** the easiest way to *implement* Π(k_i) without computing
probabilities node-by-node — list every edge's two endpoints in one flat list (a node of degree
k appears k times) and pick uniformly from that list. A node's chance of being picked is then
automatically proportional to its degree. The classic bug (human or LLM) is picking uniformly
from the *node* list instead — that silently reverts to "growth alone," no preference at all.

Growth + preferential attachment together are sufficient to generate a power law with **γ = 3**,
no fine-tuning required — the "rich get richer" / cumulative-advantage mechanism: an early lead
in degree compounds, because more links means more chances to be picked next.

**Explorable referenced:** "BA growth" — five linked experiments: hubs emerging as the network
grows, removing preferential attachment while keeping growth, removing growth while keeping
preferential attachment, first-mover advantage under both schemes.

**Exercises on this section:** 2.5a (paper — endpoint-list trick, rich-get-richer, killing the
preference, growth alone vs. a matched random graph) → 2.5b (code — build BA from n=2 to
n=5000, validate slope ≈ −3 and cross-check against `networkx.barabasi_albert_graph`, isolate
growth-only vs. preferential-attachment-only) → 2.6 (is Marvel's in-degree actually a power
law? CCDF, comparison to BA/random, LLM fact-check).

**Textbook:** Atlas Ch. 17 §17.3 *Degree Distribution*; Barabási, *Network Science*, Ch. 5
§5.1–5.5.

## 7 · Shuffling — the model becomes a test

Sections 2–6 used models as *mechanisms* (does growth + preferential attachment explain hubs?).
Section 7 repurposes the same models as **null models** instead — pure statistical baselines,
no mechanistic claim, just "what does this property look like if only the degree sequence is
held fixed and everything else about the wiring is randomized?"

**Two ways to build a degree-preserving null:**
- **Edge swapping (double edge swap):** repeatedly pick two edges A–B and C–D and rewire to
  A–D and C–B (skip the swap if it would create a self-loop or duplicate an existing edge).
  Every node keeps its exact degree; the wiring gets scrambled.
- **Configuration model:** give every node a number of "stubs" equal to its real degree, then
  pair stubs uniformly at random. Mathematically cleaner, but can generate self-loops and
  parallel edges that then need to be discarded — one reason it and edge-swapping don't always
  land on exactly the same numbers (Exercise 2.8.5).

**Why the null choice matters — Marvel clustering:** unconstrained random G(n,m) gives
C ≈ 0.04; a degree-preserving shuffle gives C ≈ 0.15; the real network is C ≈ 0.32. So hubs
(what the degree-preserving null captures) explain *part* of the excess clustering over pure
chance, but not all of it — something beyond the degree sequence alone (community structure is
the usual suspect) accounts for the rest.

**Permutation testing:** generate many shuffles, compute the statistic on each one → a
distribution of "nothing interesting, given these degrees." Compare the real network's value
against that distribution:
- **Z-score** = (real value − shuffle mean) / shuffle SD
- **Empirical p-value** = fraction of shuffles that match or exceed the real value

Marvel clustering example: 100 shuffles → mean 0.155, SD 0.009 → real value sits about 18 SDs
out (empirical p ≈ 0).

**Explorable referenced:** edge-swapping animation on Marvel's giant component (277 nodes),
comparing five quantities under both a degree-preserving null and a random G(n,m) null.

**Textbook:** Atlas Ch. 18 §18.1 *Configuration Model*; Ch. 19 §19.1 *Network Shuffling*.

## 8 · A null model in action — the friendship paradox

**The claim:** your friends have more friends than you do, on average — and in real networks
this is usually literally true, not just a feeling. Marvel: a random character averages ~10
links; a random *neighbor* of a random character averages ~25. About three-quarters of the
time, the friend really is more connected than the original character.

**Why:** degree-biased sampling. "A random friend of a random person" doesn't sample nodes
uniformly — it samples proportional to degree, exactly like the endpoint-list trick from §6.
Hubs sit in far more people's friend lists, so they get oversampled.

**The formula:** if degree has mean ⟨k⟩ and variance σ², a random neighbor's expected degree is
⟨k⟩ + σ²/⟨k⟩. The paradox is driven entirely by the *variance* of the degree distribution — the
more heavy-tailed (scale-free-like) the network, the larger σ², the stronger the paradox. With
(near-)zero degree variance the effect vanishes.

**The null-model twist:** unlike Marvel's clustering, a degree-preserving shuffle does *not*
kill the friendship paradox — only a null that removes the hubs themselves (e.g. capping
degree) substantially weakens it. Even plain random graphs show a bit of the effect, just much
less. So the paradox is a property of the *degree sequence itself*, not of how those degrees
happen to be wired together.

**Textbook:** ties back to Atlas §16.2 (Poisson vs. heavy-tailed degree distributions) and
Ch. 17 §17.3 (power laws) — the friendship paradox is really "what degree-biased sampling does
to any distribution with variance," restated as a network phenomenon.

## Quick formula box

| Quantity | Formula |
|---|---|
| G(n,p) expected links | ⟨m⟩ = p·n(n−1)/2 |
| G(n,p) expected degree | ⟨k⟩ = p·(n−1) |
| G(n,p) degree distribution | Poisson(⟨k⟩) |
| G(n,p) path length | d ≈ ln n / ln⟨k⟩ |
| G(n,p) clustering | CC_v = p |
| Giant component threshold | ⟨k⟩ = 1 |
| Expected isolates | n·e^(−⟨k⟩) |
| Local clustering coefficient | C_i = 2e_i / (k_i(k_i−1)) |
| WS model parameter | p: 0 = lattice, 1 = random |
| Preferential attachment probability | Π(k_i) = k_i / Σ_j k_j |
| BA power-law exponent | γ = 3 |
| Friendship paradox: random neighbor's expected degree | ⟨k⟩ + σ²/⟨k⟩ |
| Shuffle-test z-score | (real value − shuffle mean) / shuffle SD |

## Exercise index (this week's page)

- **2.1** — Did you really read it? — random networks 🧠 *(5 parts, all conceptual/hand-calc)*
- **2.2** — The random network, as code 🚀 *(4 parts, all coding)*
- **2.3** — The clustering coefficient, by hand 🧠 *(5 parts, hand-calc + verification)*
- **2.4** — Small worlds, quantitatively 🧠+🚀 *(4 parts, prediction + reproduction + analysis)*

Exercises 2.1-2.4 are answered in full; 2.5a-2.9 are scaffolded and in progress, in `2.1-2.9_models_and_null_models.ipynb`.
