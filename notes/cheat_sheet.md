---
Course: 02805 Social Graphs and Interactions (DTU, Fall 2026)
Purpose: running exam-prep reference for the pen-and-paper midterms. Cumulative — one section
         per week, only definitions/formulas/worked examples actually needed for hand
         calculations and read-the-figure items, not the coding exercises.
---

# Cheat Sheet — 02805

## Week 1 — Networks: the basics

*(from the site's own "Essential Definitions (Exam Scope)" list, plus the worked examples the
page actually walks through — those are fair game for "read this figure / reproduce this
number" test items.)*

- **Node, edge** — the two building blocks of a network.
- **Directed vs. undirected** — does an edge A→B imply B→A, or not?
- **Weighted vs. unweighted** — does an edge carry a strength/intensity, or just presence?
- **Simple network** — no self-loops, no multi-edges (one edge max per pair).
- **Degree** k_i — number of edges touching node i.
- **Average degree** ⟨k⟩ = 2m / n (undirected).
- **Density** = 2m / [n(n−1)] — fraction of all possible edges that actually exist. Real
  networks are almost always **sparse** (density ≪ 1).
- **Edge list** vs. **adjacency matrix** — the two standard representations. Row/column sums of
  an adjacency matrix must equal each node's degree (row = out-degree, column = in-degree, if
  directed).
- **Path, distance** — a path is a sequence of edges connecting two nodes; distance = length of
  the *shortest* path.
- **Connected component** — a maximal set of nodes all reachable from one another.
- **Isolate** — a node with degree 0 (its own component of size 1).
- **Giant component** — a component that contains a large fraction of all the network's nodes.
- **Degree distribution** — how many nodes have exactly k edges, for every k.
- **Heavy tail** — a degree distribution where the probability of large k decays much more
  slowly than an exponential (candidate: a power law).
- **Binning** — grouping degree values into (usually widening) ranges to reduce noise in a
  sparse tail; each bin's count divided by *bin width*; drawn at the bin's geometric mean; use
  k+1 as the plotted variable so that k=0 (isolates) survives a log axis.

**Choosing the representation** — before you have a network, someone decides what counts as a
node and what counts as an edge, and that choice determines every conclusion downstream.
Example: "the network of science" modeled as *papers citing papers* (nodes live forever, edges
point backward in time, hubs = classic papers) vs. modeled as *scientists co-authoring* (nodes
active for a period, edges mutual, hubs = sociable lab heads). Same underlying reality, two
networks that disagree about almost every question (who matters, what spreads, what a
community is). Neither is wrong — each answers different questions. **This is the first skill
tested on paper**: not "what did you measure?" but "why is this the network you measured it
on?"

**Average in-degree = average out-degree, always** — every directed edge has exactly one tail
and one head, so summing all out-degrees and summing all in-degrees both give m. Hence
⟨k_in⟩ = ⟨k_out⟩ = m/n even when the two *distributions* look nothing alike (Marvel: in-degree
is heavy-tailed, out-degree dies out around k=28 — same mean, very different shapes).

**Worked example — the Marvel network (week-1 snapshot)**
n = 303 nodes; 1,784 directed edges → ⟨k_in⟩ = ⟨k_out⟩ = 1784/303 ≈ 5.9. Collapsed to undirected
pairs: m = 1,434 (350 of them reciprocated both ways) → ⟨k⟩ = 2m/n = 2·1434/303 ≈ 9.5. Density:
n(n−1)/2 = 45,753 possible pairs, 1,434 exist → density ≈ 1434/45753 ≈ 0.031 (about 3% — "dense"
only by the standards of real networks, most of which sit under 1%). 17 characters are
isolates. One giant component of 277 characters (91% of the network) plus one island of 9.
*Every number here follows from n, m and the edge list alone — which is exactly why the
pen-and-paper test likes this kind of question.*

**Reading a network drawing — data vs. decoration.** Force-directed layout pulls linked nodes
together and pushes others apart — for a few hundred nodes it reveals clusters, hubs and
loners, but positions come from a physics simulation, so stay critical. Circular layouts
(A–Z, or ordered by degree) only reorder position around a ring; the *only* extra information
any circular layout adds is whatever you sorted by. Random layout carries zero positional
information — it's the baseline for "what force layout is adding." Across every layout: the
number of nodes, the number of edges, any single node's degree, and the network (graph)
distance between two nodes never change — that's data. How far apart two nodes *look* on
screen changes with the layout — that's decoration, and closeness on screen can come from real
network proximity or just from how the layout algorithm happened to settle.

**Read-the-figure basics:** linear vs. log–log axes; force-directed vs. circular vs. random
layouts (see above; Week 1 Exercise 1.7).

## Week 2 — Models & null models

*(the site hasn't posted an official "Essential Definitions" list for Week 2 yet — compiled
from Exercises 2.1–2.9 and Sections 1–8's published prose. See `week2_models_and_null_models.md`
for the full write-up.)*

**Erdős–Rényi random graph G(n,p)** — connect every pair of n nodes independently with
probability p.
- ⟨m⟩ = p·n(n−1)/2, ⟨k⟩ = p·(n−1)
- Degree distribution: **Poisson**, mean ⟨k⟩ — short-tailed.
- Path length: d ≈ ln n / ln⟨k⟩ (grows only logarithmically).
- Clustering: CC_v = p (essentially zero for sparse networks).
- **Giant component appears at ⟨k⟩ = 1** (phase transition). Below: fragments, size grows
  logarithmically with n. Above: one component holds a finite fraction of n, grows linearly.
- Expected number of isolated nodes: n·e^(−⟨k⟩).
- Marvel-sized random graph (n=303, p=0.031): biggest hub only reaches k≈19, vs. real
  Spider-Man's 106; randomized-Marvel average distance ≈2.8 hops (vs. real 2.67–2.8, essentially
  the same — short paths are *not* surprising on their own).

**Six degrees / small-world property** — real networks (like random graphs) have distances
that grow only logarithmically with size — "short paths" is not, by itself, surprising;
clustering is where random graphs fail.

**Clustering coefficient**
- Local: C_i = 2e_i / (k_i(k_i−1)), where e_i = edges actually present among i's k_i neighbors.
  Undefined (0/0, reported as 0) for k_i ≤ 1.
- Network average C = mean of all C_i (weights every *node* equally).
- **Transitivity** = triangles / connected triples (weights every *triad* equally — pulled down
  harder by hubs than C is; the two coincide only in a regular graph). Marvel: C≈0.31 but
  transitivity≈0.18 — hubs pull transitivity down harder because they touch many more triples.

**Watts–Strogatz model** — ring lattice, rewire each edge with probability q.
- q = 0: lattice — high clustering, path length grows linearly with n (distances ~ n, not
  log n).
- q = 1: (approximately) random graph — low clustering, path length ≈ ln n / ln⟨k⟩. **Not
  exactly** G(n,p): edge count is fixed by construction and the degree distribution is narrower
  (higher minimum degree) than a true Poisson.
- Small q (~0.001–0.1): both high clustering *and* short paths — "small-world" regime.
  Clustering degrades slowly with q (a purely local effect — the 99% of un-rewired links keep
  it); path length collapses fast (a single shortcut/rewired link can shorten many pairs'
  distances at once).
- **Giant component: always 100% of n, for any q** — rewiring relocates edges, never removes
  them, so connectivity is guaranteed by construction.
- **Worked example — matching Marvel:** real Marvel has C≈0.31, average distance 2.7 (diameter
  6). A Watts–Strogatz network with Marvel's n and ⟨k⟩ at q≈0.2 lands C right on 0.31, and at
  that same setting the average distance is 3.1 hops — *both* numbers from one model. The random
  graph could only ever match one (C≈0.03, distance≈2.8).

**Preferential attachment / Barabási–Albert model**
- Two ingredients: **growth** (nodes added over time) + **preferential attachment**
  Π(k_i) = k_i / Σ_j k_j (new nodes prefer high-degree targets). Endpoint-list trick: list
  every edge's two endpoints, pick uniformly from that list — implements Π(k_i) exactly.
- Produces a power-law degree distribution P(k) ~ k^(−γ) with **γ = 3**, no tuning needed.
- Explains **hubs**: nodes with far more links than average (Marvel's Spider-Man: degree 106 vs.
  network average 9.5; a matched random graph tops out around max degree 19).
- **Clustering:** C(n) ~ (m/8)·(ln n)²/n — decays with n; plain BA does *not* reproduce real
  networks' high clustering (same weakness as a random graph here).
- **Path length:** d ≈ ln n / ln(ln n) — "ultra-small-world," even shorter than a random graph's.
- **Giant component:** always 100% of n, by construction — every arriving node brings its own
  edge(s), so there are never isolates.
- **Natural cutoff (expected max degree):** k_max ~ m·n^(1/(γ−1)) = m·√n for γ=3 — the power-law
  analogue of the random-graph extreme-value cutoff (§6's "why 19, not 106" calculation).
- **Why in-degree but not out-degree:** in-links are conferred by others (preferential
  attachment applies directly); out-links are authored (effort + a natural page-length budget
  caps them) — that's why Marvel's in-degree is heavy-tailed and its out-degree isn't.

**CCDF (complementary cumulative distribution function)** — P(K ≥ k), fraction of nodes with
degree at least k. Preferred over binned P(k) for spotting power laws: monotonic, no binning
choices, uses every data point. A power-law P(k) shows as a straight line on log–log CCDF axes
too (with a shifted slope: CCDF exponent = γ − 1). A straight line establishes a **heavy tail**,
not by itself a power law with a specific γ (log-normal and power-law-with-cutoff look similar).

**Null model** — a randomized baseline used to test whether an observed property is
"surprising" given some constraint (e.g. the degree sequence), not a claim about mechanism.
Choosing the null changes the *conclusion*, not just the number.
- **Configuration model** — give each node stubs = its degree, pair stubs uniformly at random;
  can create self-loops/parallel edges that must be discarded.
- **Degree-preserving shuffle (double edge swap)** — repeatedly rewire edge pairs A–B, C–D →
  A–D, C–B, skipping self-loops/duplicates; keeps every node's exact degree. This is what "the
  adjacency matrix is being shuffled" means: permute entries, keep every row sum.
- **Shuffle test**: run the shuffle many times, compute the statistic on each →
  Z-score = (real − shuffle mean)/shuffle SD; empirical p-value = (1 + #shuffles ≥ real) /
  (1 + #shuffles) (never exactly 0, however many shuffles you run).
- **General recipe:** (1) decide which properties are given/kept (usually n, m, degree
  sequence), (2) generate many networks keeping exactly those, scrambling everything else,
  (3) measure your quantity on every one, (4) compare the real value: z-score or the fraction
  of shuffles at least as extreme.
- **Worked example — Marvel clustering, properly nulled.** Random-graph null: C = p ≈ 0.04 —
  wrong question, it has no hubs. Degree-preserving shuffle (has the hubs): C falls from the
  real 0.32 (giant component) to a shuffle mean of **0.155, SD 0.009** — the real value sits
  **≈18 standard deviations out** (z≈18; no shuffle will ever reach it, empirical p≈0). So hubs
  explain *some* of the clustering surplus (0.04→0.155) but far from all of it (0.155→0.32).
  *Flawed AI sentence to recognize:* "our clustering (0.31) is 10× an Erdős–Rényi network's
  (0.03), proving the clustering is caused by the heavy-tailed degree distribution" — the ER
  baseline has no hubs, so it cannot show what the hubs alone would produce; only the
  degree-preserving shuffle can answer that question, and it still leaves a huge gap.
- **Two roads to the same null can disagree** — the configuration model (drop self-loops/
  parallel edges) lands visibly lower (~0.11) than degree-preserving edge swaps (~0.15) on the
  same network; check which links you dropped and whose they were before treating "the null"
  as one number.

**Reciprocity — another null-model trap.** 39% of directed Marvel links are reciprocated
(A→B and B→A); a random directed network of the same density gives only ≈3% (13× less) — but
before calling that "13× higher than chance," ask what a *better* null does: hubs cross-link
each other's reciprocated ties too, so a degree-preserving null shrinks the effect. Same
lesson as clustering: the easiest null to generate is not always the right one.

**Friendship paradox** — a random neighbor's expected degree is ⟨k⟩ + σ²/⟨k⟩ (σ² = degree
variance); driven purely by variance, so strongest in heavy-tailed/scale-free networks, weakest
in random ones (a Poisson still has variance > 0, so the paradox never fully vanishes). Survives
a degree-preserving shuffle (only removing the hubs themselves kills it) — unlike excess
clustering, which a degree-preserving shuffle *does* mostly explain away.
- **Worked example — Marvel:** a random character has ⟨k⟩≈10 links; a random *neighbor* of a
  random character averages ≈25 links. In 3 of every 4 samples, the friend is at least as
  connected as you are.

**Quick formula box (Week 2)**

| Quantity | Formula |
|---|---|
| G(n,p) expected links | ⟨m⟩ = p·n(n−1)/2 |
| G(n,p) expected degree | ⟨k⟩ = p·(n−1) |
| Giant component threshold | ⟨k⟩ = 1 |
| Expected isolates | n·e^(−⟨k⟩) |
| Local clustering coefficient | C_i = 2e_i / (k_i(k_i−1)) |
| Preferential attachment probability | Π(k_i) = k_i / Σ_j k_j |
| BA power-law exponent | γ = 3 |
| Friendship paradox | random neighbor's E[degree] = ⟨k⟩ + σ²/⟨k⟩ |
| Shuffle-test z-score | (real − shuffle mean) / shuffle SD |
| Empirical p-value | (1 + #shuffles ≥ real) / (1 + #shuffles) |

## What a random-graph null model gets right vs. wrong (running theme)

| Property | G(n,p) reproduces it? |
|---|---|
| Giant component | ✅ yes |
| Short average path length | ✅ yes |
| Clustering | ❌ no (CC_v = p, far too low) |
| Isolated nodes as a distinct population | ❌ no (expected ≈ 0) |
| Hubs / heavy-tailed degree distribution | ❌ no (Poisson, short-tailed) |

Watts–Strogatz fixes the clustering row; Barabási–Albert (Week 2 §6) fixes the hubs row.

## Week 3 — Who matters, and why

*(from the site's "on paper, closed book" skills list, plus the worked examples the page
builds each definition around. See `week3_centrality_and_mixing.md` for the full write-up.)*

**Walk, path, distance** — walk = any sequence of linked nodes; path = never repeats a node;
distance d_ij = shortest-path length (∞ if unreachable).
**BFS** — expand ring by ring from a start node; the ring a node first appears in is its
distance. **Eccentricity/diameter/radius/center** — a node's farthest distance / the largest
eccentricity / the smallest / node(s) at the radius.
**Weakly vs. strongly connected (directed only)** — weakly: connected ignoring direction;
strongly: every node reaches every other *following the arrows*. Marvel's biggest SCC: 229/303.

**Worked example — paths on Marvel.** Giant component: ⟨d⟩ = 2.67, diameter 6, radius 3, center
= Spider-Man (nobody is more than 3 undirected steps from him); 86% of all character pairs sit
exactly 2–3 steps apart. Keep the arrows: from Spider-Man's own page you can reach only 230 of
303 characters (46 are simply never reached, because his page links out to just 9 characters).
Largest strongly connected component: 229/303 (everyone in it can reach everyone else *and* be
reached, following arrows both ways).

**Degree centrality k_i** — local only; directed → split into in-/out-degree. *Worked example:*
Hulk is mentioned by 64 pages (2nd highest in-degree) but his own page mentions only 10
characters; Betsy Braddock is mentioned by just 7 pages but her page mentions 28 (the most of
anyone) — in- and out-degree answer different questions ("who's talked about" vs. "who talks").

**Closeness:** C_close = (n−1) / Σ_j≠i d_ij — breaks (=0) if any node is unreachable. *Worked
example:* Spider-Man's closeness is 0.59 (mean distance 1.68 hops); the median character sits
at 0.38.
**Harmonic centrality (the fix):** C_harm = (1/(n−1)) Σ_j≠i 1/d_ij, with 1/∞ = 0. Works on
directed/disconnected networks; on a connected network the two rankings agree almost exactly.

**The Medici story (motivating example for betweenness).** Florence, ~1430: John Padgett's
reconstructed marriage network of the ruling families. The Medici had 6 marriage ties — not
dramatically more than the Strozzi or Guadagni (4 each) — yet within a few years Cosimo de'
Medici controlled the city. Why: of the Medici's six partner families, only one pair was tied
to *each other* — every other family that needed to deal with a Medici partner had to go
*through* the Medici. More than half of all shortest paths between the other families ran
through the Medici, twice any rival's share. **Not the best-connected family — the family in
between.** This is exactly what betweenness captures and degree does not.

**Betweenness:** b_i = Σ_(s≠i≠t) σ_st(i)/σ_st, where σ_st = # shortest s→t paths, σ_st(i) = #
of those through i (ties split fractionally). Divide by (n−1)(n−2)/2 (undirected) to normalize
to [0,1], which is what networkx reports. Can be high at low degree (sole gateway) or ≈0 at
high degree (neighbors already linked to each other). Measures **control** — brokers/bridges/
bottlenecks, computed in O(nm) total via Brandes' algorithm (one BFS + back-propagation per
node).

**Krackhardt's kite** — a 10-node, 18-link toy network built specifically to make centralities
disagree. Degree crowns node D; closeness crowns F and G; betweenness crowns H; eigenvector
crowns D again. Remove H and nodes I, J are cut off from the rest of the network (their
closeness collapses); remove D instead and whoever is now best-linked to the remainder takes
over. Referenced repeatedly in the exercises — worth being able to compute betweenness/
closeness on by hand if given the drawing.

**Worked example — betweenness, compared to what.** Spider-Man: 23% of all shortest paths run
through him — but 200 degree-preserving shuffles give the *same* 23% on average, so this is not
a finding, just what a 106-link node does in any network with this degree distribution.
Hercules (26 links): betweenness 0.037 vs. 0.018 in the shuffles — **4 SD out**, a genuine
broker (bridges the Avengers, the Hulk's circle, the cosmics, and Asgard). Black Widow (25
links): betweenness ≈2× her shuffled value. Black Cat (28 links): betweenness only **1/3** of
what her degree predicts — 24 of her 28 neighbors are also Spider-Man's neighbors, so almost
every path near her has a shortcut around her. *Flawed AI sentence to recognize:* "23% of
shortest paths pass through Spider-Man, confirmed by his closeness of 0.59, showing he can
reach 59% of the network directly" — the 23% is not a finding (see above), and closeness is an
*inverse mean distance*, not a fraction of the network reached; misreading it is a distinct
error from the first one.

**Eigenvector centrality:** x_i = (1/λ) Σ_j A_ij x_j — important iff connected to important
nodes; solved by power iteration (start all-ones, replace each score by the sum of neighbors'
scores, rescale, repeat).
**PageRank (directed):** PR_i = (1−α)/n + α Σ_(j→i) PR_j/k_j^out, α=0.85 by convention — models
a random surfer who teleports with probability 1−α; fixes dangling nodes and SCC traps that
break plain eigenvector centrality on directed networks. *Worked example:* Spider-Man's page
links to only 9 characters, so each gets roughly a ninth of the network's largest "vote";
Black Cat and Mayday Parker have modest in-degrees (21 and 14) yet land at PageRank ranks 5
and 7 because of it.
**Random-walk view (undirected):** stationary distribution π_i = k_i/2m — proportional to
degree (undirected PageRank reduces to plain degree).

**Rank correlations on Marvel** (how much the measures agree): degree↔betweenness 0.91,
degree↔eigenvector 0.88, eigenvector↔closeness 0.98 (the strongest agreement — closeness is
squeezed into a narrow 0.2–0.6 range so it can barely tell the hubs apart from each other).

**Null models still apply:** always (1) say which question a centrality answers (degree =
popularity, closeness = reach, betweenness = control, PageRank/eigenvector = prestige), and
(2) say compared to what — a centrality is only meaningful relative to a null; the
degree-preserving shuffle answers "is this node's position more than its degree?"

**Degree assortativity r** — Pearson correlation of degree at the two ends of every edge.
r > 0 = assortative (hubs → hubs, typical of social networks); r < 0 = disassortative (hubs →
leaves, typical of tech/bio networks). Reference values: physics co-authorship +0.36, film
actors +0.21 (assortative/social); Internet −0.19, protein interactions −0.16 (disassortative/
tech-bio); a pure star network has r = −1. Marvel: real r = −0.105 vs. shuffle −0.118 ± 0.009 →
not significantly disassortative (**structural disassortativity** — the degree distribution
alone explains it: a 106-link hub in a 277-node component simply cannot find enough other hubs
to link to). Pushing the rewiring as hard as possible: the assortative side stalls near
r = +0.17 (hubs run out of other hubs), the disassortative side reaches r = −0.53; an ordinary
degree-preserving shuffle lands near r ≈ −0.12 — none of that is "0," which is the point.
**Average neighbor degree k_nn(k)** — rising with k → assortative; falling → disassortative;
flat (at ⟨k²⟩/⟨k⟩) → no mixing pattern.
**Homophily** — assortative mixing by an *attribute* rather than degree; tested by shuffling
labels, not edges (and, if the attribute correlates with degree, by shuffling labels only
*within* degree bins, so the result isn't just "the famous ones are hubs").

**Clique** — every pair of nodes linked. **Maximal clique** — none can be added. **Clique
number** — size of the largest clique. A k-clique has k(k−1)/2 edges. Marvel: 1,835 triangles,
477 5-cliques, clique number 8 (an all-X-Men group: Betsy Braddock, Cable, Cyclops, Emma Frost,
Jean Grey, Northstar, Rachel Summers, Wolverine).

**Quick formula box (Week 3)**

| Quantity | Formula |
|---|---|
| Closeness centrality | C_close = (n−1) / Σ_j≠i d_ij |
| Harmonic centrality | C_harm = (1/(n−1)) Σ_j≠i 1/d_ij |
| Betweenness centrality | b_i = Σ σ_st(i)/σ_st over pairs s≠i≠t |
| Eigenvector centrality | x_i = (1/λ) Σ_j A_ij x_j |
| PageRank | PR_i = (1−α)/n + α Σ_(j→i) PR_j/k_j^out (α=0.85) |
| Random-walk stationary dist. (undirected) | π_i = k_i/2m |
| Degree assortativity | r = Pearson corr. of endpoint degrees |
| k-clique edge count | k(k−1)/2 |

**Which centrality for which question**

| Question | Measure |
|---|---|
| Most direct contacts? | Degree |
| Fastest to reach everyone? | Closeness / harmonic |
| Removal disrupts the most traffic? | Betweenness |
| Connected to other important nodes? | Eigenvector / PageRank |
| Vaccination priority | Degree |
| Retirement/removal impact on an org | Betweenness |
| Airport closure delaying the most routes | Betweenness |

## Week 4 — Communities & backbones

*(from the site's "Essentials" band and the "Test 1" skills list, all 8 sections. See
`week4_communities_and_backbones.md` if you want the full write-up someday — for now this
section is complete for exam purposes.)*

**Community** — a set of nodes more densely connected among themselves than to the rest of the
network (Coscia's version: if two nodes are in the same community, they are more likely to be
connected). **Partition** — every node in exactly one community (so it can't capture overlap).

**The Zachary karate club (motivating example, referenced across the week's exercises).** Wayne
Zachary spent three years watching a university karate club (34 members, 78 friendship links)
that split into two factions after a dispute between the instructor ("Mr. Hi") and the
president. Zachary asked everyone who they sided with — giving the network rare *ground truth*.
Girvan–Newman's first cut is the link Mr. Hi (node 0) – member 31 (edge betweenness 71.4, far
ahead of the runner-up at 43.8); after 11 cuts the club splits into groups of 19 and 15,
matching the real factions on all but one member (who stayed with the instructor's side purely
because he was three weeks from his black-belt exam — a reason no network could see). The real
split scores **Q = 0.358** (67 of 78 friendships stay inside a faction; 39 expected by chance).
It became network science's most overused toy example (the "Zachary Karate Club Club" trophy
joke, started 2013, awarded to whoever puts it on a conference slide).

**Edge betweenness** — number of shortest paths (over all node pairs) that run along a link;
ties split fractionally (1/# of tied paths). Links *between* communities score high: every
path from group A to group B must squeeze through the few bridges (a single bridge carries all
n_A·n_B pairs), while links inside a dense group share traffic with many alternatives.
*Worked example (benchmark, three planted communities of 28/32/40 nodes):* the first cut
carries 286.4 shortest paths; by cut 13 the top surviving value exceeds 1,000; cut 15 removes
the last link between a 68-node and a 32-node group, carrying exactly 68×32 = 2,176 paths (one
per pair across); right after that cut the recomputed values drop to 183; cut 27 leaves exactly
the three planted groups, the dendrogram's best level, Q = 0.571.

**Girvan–Newman (top-down, divisive)** — (1) compute edge betweenness, (2) remove the
highest link, (3) **recompute everything**, (4) repeat. Output: dendrogram from one blob to
single nodes. Cost O(m²n) — too slow for anything but small/medium networks (hours on the
philosophers' 9,139 links vs. under a second for Louvain).
- One removal doesn't necessarily split the network — keep removing until it disconnects.
- After a split, betweenness is recomputed on the whole network (only still-connected pairs
  count); the next cut is the global maximum, wherever it is.
- **Why recompute:** two parallel bridges share traffic (~half each); remove one and the
  other now carries *all* of it. Computing once and removing in order could cut internal
  links before that second bridge.
- The dendrogram doesn't say where to stop → cut at the level with **max Q**.

**Modularity Q** — fraction of links inside communities minus the fraction expected under a
degree-preserving null:
- Per-community (use this by hand): **Q = Σ_c [ ℓ_c/m − (d_c/2m)² ]**
  - ℓ_c = links with both ends inside c; d_c = sum of degrees of c's nodes (links leaving c
    count in d_c but in no ℓ_c).
  - (d_c/2m)² = chance both ends of a random link land in c (2m stubs, d_c of them in c).
- Matrix form (on formula sheet): Q = (1/2m) Σ_ij (A_ij − k_i k_j/2m) δ(c_i,c_j) — same thing.
- One community → Q = 0 exactly. Every node alone → Q = −Σ_i (k_i/2m)² (slightly negative).
  Bad partition → can be negative. Real networks: Q ≈ 0.3–0.7 (rule of thumb, not a test —
  see "random networks have Q > 0" below).
- **Q measures "how grouped", not "how right"** — Zachary's real split Q = 0.358, but moving
  the misclassified member (node 8) raises Q to 0.372; moving member 2 instead *drops* it to
  0.329; moving Mr. Hi (node 0) collapses it to 0.166. Girvan–Newman's own best 2-way split
  scores Q = 0.360 (barely above the real split); the dendrogram's actual best level is 5
  groups at Q = 0.401 (after 24 cuts); Louvain finds 4 groups the club never historically had,
  at Q = 0.420.
- Check: Σ_c d_c = 2m. Symmetric communities → compute one term, multiply.

**Worked example (two triangles A–B–C, D–E–F + bridge C–D):** m = 7, degrees 2,2,3,3,2,2.
{A,B,C}·{D,E,F}: each term 3/7 − (7/14)² = 5/28 → Q = 5/14 ≈ 0.357.
{A,B,D}·{C,E,F}: each 1/7 − 1/4 → Q = −3/14 ≈ −0.214. All in one: Q = 0.
Edge betweenness: C–D = 3·3 = 9; A–C = B–C = 4; A–B = 1 → remove C–D first.

**Merge gain** (joining communities a and b, ℓ_ab = links between them):
**ΔQ = ℓ_ab/m − 2·(d_a/2m)(d_b/2m)**
(derivation: the ℓ_a, ℓ_b, d_a², d_b² terms cancel; only the cross-term 2d_a d_b survives).
Hand trick: over a common denominator (2m)², ΔQ = [4m·ℓ_ab − 2 d_a d_b] / (2m)²
(e.g. m = 7: 1/7 = 28/196, so each link between a and b is worth 28/196).

**Greedy modularity (Newman 2004, bottom-up, agglomerative)** — we do *not* know the
communities in advance: start with every node alone (n communities), repeatedly merge the
pair of linked communities with the largest ΔQ, keep merging to one community (even when ΔQ
< 0), keep the level with max Q. "Greedy" = merges are never undone → early mistakes lock in
(philosophers: 15 communities, Q = 0.416, three giant blobs — one of them puts Heraclitus and
Plotinus together with Bertrand Russell and Einstein).
Two-triangle run: Q = −0.173 → −0.071 (A+B) → 0.092 (+C) → 0.194 (E+F) → **0.357** (+D) → 0.

**Louvain (Blondel et al. 2008)**
- Phase 1 (move nodes): start with every node alone; visit nodes in turn, move each into the
  neighboring community that raises Q the most (stay if nothing helps); sweep until a full
  pass moves nobody. Q only goes up, never down.
- Phase 2 (aggregate): each community → one super-node; links between communities → weighted
  links; links inside → weighted self-loops. Repeat phase 1 on the smaller network.
- **Why aggregate:** at the end of phase 1 no *single* node can improve Q, but moving a
  *whole group* might (a lone member leaving loses its ties to the rest). On super-nodes,
  "moving one node" = moving a whole group.
- Fast (one sweep ≈ one read of the edge list). **Seed-dependent** (node visiting order) → no
  guarantee of the global max Q.
- Philosophers: 1,374 nodes → phase 1 (1,794 moves over two full sweeps, crossing the
  shuffled-network line of Q=0.228 at move 1,226) → 65 groups, Q = 0.458 → level 2 (73
  moves) → level 3 (2 moves) → **8 communities, Q = 0.506**. Named after each group's
  highest-degree member: Aristotle (Greek/Roman antiquity), Aquinas (Christian thought,
  Augustine→Dante→Luther), Kant (German philosophy, Hegel→Marx→Nietzsche), Descartes (early
  modern Europe/Enlightenment), Russell (20th-century founders, incl. Einstein), the Buddha
  (Indian philosophy), Confucius (Chinese philosophy, incl. Mao), Avicenna (medieval
  Islamic/Jewish philosophers *plus* Galileo, Copernicus, Bacon — "not a school anyone would
  name," a reminder that **the names are labels of the partition; the story is told
  afterward**).

**Random networks have Q > 0** — the optimizer always finds *some* partition with fewer
crossing links than expected. Philosophers shuffled (degree-preserving): Q = 0.228 ± 0.002
(Marvel: 0.25); G(n,m): 0.233; sparse ⟨k⟩ = 2: Q ≈ 0.8 (the sparser the network, the easier it
is to find borders that few links cross, so "0.3–0.7 means real structure" is a rule of thumb,
not a test). Compare against the **degree-preserving** null (same degrees as the real
network) → report the difference or the z-score, never Q alone.

**NMI — Normalized Mutual Information** — how much two partitions of the *same* nodes agree.
**1 = identical** (even if the labels are renamed), **0 = independent** (knowing a node's
group in one tells nothing about the other). Only "who is with whom" matters, never the
label names.
- n = # nodes; n_x, n_y = community sizes in partitions 1 and 2; n_xy = # nodes in both x
  and y (overlap table).
- Entropies: **H_1 = −Σ_x (n_x/n) log(n_x/n)**, **H_2 = −Σ_y (n_y/n) log(n_y/n)**
  (= uncertainty about a random node's group).
- Mutual information: **I = Σ_x,y (n_xy/n) · log[ n·n_xy / (n_x·n_y) ]**
  (= how much knowing the group in one partition reduces uncertainty about the other).
  n_x·n_y/n = expected overlap if independent → log(observed/expected); cells with n_xy = 0
  contribute 0; a term is negative when overlap is below chance.
- **NMI = 2I / (H_1 + H_2)**. Log base cancels (use log₂).
- Steps by hand: (1) build the overlap table n_xy, (2) H_1 and H_2, (3) I over non-zero
  cells, (4) normalize.
- Example (6 nodes): {A,B,C}·{D,E,F} vs {A,B,C,D}·{E,F} → table [[3,0],[1,2]];
  H_1 = 1, H_2 = 0.918, I = ½log₂1.5 + ⅙log₂0.5 + ⅓log₂2 = 0.459 → **NMI ≈ 0.48**
  (one misplaced node in 6 costs a lot).
  {A,B,C}·{D,E,F} vs {A,D}·{B,E}·{C,F} → every cell n_xy = 1, log₂(6·1/(3·2)) = 0 → **NMI = 0**.
- Code: sklearn.metrics.normalized_mutual_info_score(labels1, labels2). networkx has no NMI
  function.

**Reading NMI values (week 4 numbers)**

| Comparison | NMI | Meaning |
|---|---|---|
| Louvain, different seeds — philosophers | 0.65–0.83 | agree on the core, disagree on borders |
| Louvain, different seeds — Marvel | ~0.59 | as much disagreement as agreement |
| Random network, ⟨k⟩ = 5, Q = 0.45 | ~0.20 | high Q, no stable structure = noise |
| Philosophers vs `era` (century list) | 0.40 | communities are traditions, not centuries |
| Philosophers vs `movement` (Wikidata) | 0.49 | still someone else's reading, not "truth" |

**High Q + low NMI between runs = alarm** (score without structure).
Two runs with Q = 0.505 vs 0.506 do **not** mean the same communities — check NMI.

**Honest community report** = Q **and** the null (shuffled Q / z-score) **and** stability
(NMI across seeds). *Flawed AI sentence to recognize:* "Louvain detected 9 communities with a
modularity of 0.50, proving that the history of philosophy divides into nine schools." Three
flaws: (1) no null — a shuffled network scores 0.23, so we can't tell a strong 0.50 from a weak
one without it; (2) no stability check — other seeds give 8 or 10 communities at NMI 0.65–0.83
with this run, so "the nine" is one run's nine; (3) "schools" is a post-hoc story — one
community mixes Avicenna with Galileo, and the partition only agrees with century lists at
NMI 0.40.

**k-clique communities (clique percolation)** — Palla, Derényi, Farkas & Vicsek, 2005. Two
k-cliques are **adjacent** if they share k−1 nodes. A **k-clique community** is a connected set
of adjacent k-cliques (roll from one k-clique to the next across a shared (k−1)-face). Result:
communities **overlap** (a node in two adjacent-but-distinct chains of cliques belongs to both),
and a node in no k-clique at all belongs to **no community** — this is not a partition. Software:
CFinder; in Python, `networkx.community.k_clique_communities(G, k)`. k acts as a "resolution
dial" — small k percolates almost everything into one giant community (a phase transition, the
same flavor as week 2's random-graph giant component); large k leaves most nodes out entirely.
Overlap nodes tend to be the hubs.

| k | communities | largest | philosophers in a community | in two or more |
|---|---|---|---|---|
| 3 | 19 | 1,155 | 1,189 (87%) | 29 |
| 4 | 36 | 817 | 909 (66%) | 86 |
| 5 | 40 | 467 | 555 (40%) | 112 |
| 6 | 39 | 171 | 304 (22%) | 86 |

At k=5, Aristotle sits in 6 communities at once (Augustine, Aquinas, Nietzsche in 5 each) —
exactly the point: a partition would have to put him in only one tradition and be wrong about
the rest. There is no "right" k — report the one you chose, like any parameter.

**Link communities (overlap via clustering links, not nodes)** — Ahn, Bagrow & Lehmann, 2010.
Idea: nodes are ambiguous (you belong to many contexts at once) but *links* are usually
unambiguous (a specific tie is usually "about" one context). Two links sharing a node, i–k and
j–k, are similar by a Jaccard-style score over the *inclusive* neighborhoods of i and j (shared
neighbors ÷ neighbors either has). Cluster links by that similarity (single-linkage
hierarchical clustering) → each cluster is a **link community**; every node inherits every
community its links belong to, so overlap falls out for free instead of being bolted on.
**Partition density D** (the modularity-equivalent for scoring where to cut the link
dendrogram): a community with n_c nodes needs at least n_c−1 links (a tree) and can have at
most n_c(n_c−1)/2 (a clique); D measures how far its m_c links sit between those two extremes,
averaged over communities weighted by their link count. Cut the dendrogram at the height where
D peaks (the newer "adaptive cut" lets every branch pick its own height — a Goodies-level
refinement, not on the test). **Best suited to dense, highly-overlapping networks** (e.g.
Marvel: on the link-community view Spider-Man is a member of 23 different communities) —
Louvain/modularity is the better tool for a network like the philosophers that has real,
mostly-non-overlapping structure. **Weakness (the "overlap paradox," Atlas 38.7):** methods
like this and k-clique communities are bad at the sparse, non-overlapping parts of a network —
those nodes/links end up unassigned to any meaningful community, and overlap nodes (who sit
*between* groups) get ranked as *least* community-like by density-based node measures, which
is backwards from what you'd want.

**Weights: strong ties and weak ties.** A weighted edge carries w_ij. **Strength**
s_i = Σ_j w_ij replaces degree as "how connected." On the philosophers, strength and degree
rank nodes almost identically (Spearman 0.96; Aristotle leads both, strength 521 from degree
300) — but the exceptions matter: Diogenes Laertius has only the 15th-highest degree (91) yet
the 5th-highest strength (230), because his book *Lives of the Eminent Philosophers* is cited
over and over by other philosophers' pages. The strongest individual ties tell a story on their
own: Erasmus–Thomas More (weight 24, close friends), John Adams–Thomas Jefferson (22, fifty
years of rivalry and letters, died the same day), Whitehead–Russell (19, *Principia
Mathematica*). **Weighted distance:** treat a strong tie as a short distance, link length =
1/w_ij, shortest path via **Dijkstra's algorithm** instead of BFS. *Worked example:* Hume and
Marx are 2 unweighted hops apart (through any of 22 middlemen, e.g. Adam Smith); the shortest
*weighted* route is one hop longer — Hume → Kant → Hegel → Marx, over links of weight 7, 7, 10
— arguably the more meaningful "route" (the one a history-of-philosophy lecture would take).
**Weighted modularity:** same Q formula with A_ij→w_ij, k_i→s_i, m→total weight. Weighted
Louvain on the philosophers finds 9 communities at weighted Q = 0.55, vs. unweighted Q = 0.50 —
**the two numbers are not comparable** (different questions; strong ties concentrate inside
groups almost by definition, so the weighted score has a structurally higher ceiling). Always
compare a weighted Q to its own weighted-shuffle null, never to the unweighted number.

**Backbones: seeing structure in the hairball.** A hairball in a force layout doesn't mean
there's no structure — it can mean the network's too big to lay out well, has heavy overlap, or
has a hub obscuring everything else. A **backbone** keeps only the links that matter, so a
layout of *it* can actually be read.
- **Global threshold** (keep every link with w ≥ θ) is the naive approach: on the philosophers,
  w ≥ 3 keeps 1,572 links and 863 philosophers — but it throws away the *wrong* things. A
  weight of 2 is nothing to Aristotle (strength 521) but might be the single strongest tie a
  minor philosopher has; a global threshold keeps a hub's 50th-strongest link while discarding
  a small node's only meaningful one. The backbone becomes "the hubs talking to each other."
- **Disparity filter** (Serrano, Boguñá & Vespignani, 2009) — a *per-node* null model. Each
  link carries a share p_ij = w_ij/s_i of node i's strength. Null: node i's strength spread
  uniformly at random over its k_i links. Under that null, the chance one link gets a share of
  at least p_ij is (1−p_ij)^(k_i−1). A link is **significant for i** when that probability is
  below a chosen level α: (1−p_ij)^(k_i−1) < α. **Keep a link if it is significant at either
  end** — this way a link can matter for a small node even if it's negligible for a hub, and
  vice versa.
  - *Worked example:* the weight-2 link between Aristotle (strength 521) and Moses of Narbonne
    (strength 11, degree 10, a minor 14th-century commentator). For Aristotle it's nothing. For
    Moses: p = 2/11, (1−2/11)^9 = 0.16 < α = 0.2 → **kept**, because it matters enormously to
    him even though it's invisible to Aristotle. Aristotle's own weight-2 ties fail the test on
    his side (at α=0.2 he needs a link worth >0.54% of his strength, i.e. weight ≥3) and
    survive only when the *other* end needs them.
  - **Table (philosophers):**

| α | links kept | philosophers with a link | giant component |
|---|---|---|---|
| 0.05 | 292 (3%) | 348 | 116 |
| 0.10 | 649 (7%) | 607 | 419 |
| 0.20 | 1,540 (17%) | 950 | 816 |
| 0.30 | 2,549 (28%) | 1,111 | 1,052 |
| 0.50 | 5,641 (62%) | 1,284 | 1,270 |

  - **Disparity filter vs. threshold, head to head:** at α=0.2 vs. w≥3, similar link counts
    (1,540 vs 1,572) but the disparity filter keeps 950 philosophers attached vs. only 863 for
    the threshold — 112 philosophers (Moses of Narbonne among them) are rescued by the filter
    and dropped by the threshold, every one of them because their strongest tie is a lonely
    weight-2 link that means everything to them and nothing to the hub on the other end.
  - There is **no "right" α** — it's a parameter you choose and must be ready to defend, like
    any other.

**The five drawing rules** (in order — document every step in a report):
1. **Backbone first** — if the network needs filtering, use a method you've thought about and
   a parameter you can defend; state how many links/nodes were removed.
2. **Then the layout** — lay out the *backbone*, not the full network (that's what makes a
   force layout legible at all).
3. **Color by community** — only if the network has real, tested community structure (Q vs.
   its null); detect communities on the *full, unfiltered* data, never on the backbone (the
   backbone is for drawing, not for analysis); group/label the communities too, since roughly
   1 reader in 12 can't tell your green from your orange.
4. **Size by degree, strength, or centrality** — so importance is visible even without labels.
5. **Label the important nodes** — so the reader can get oriented.

**Quick formula box (Week 4)**

| Quantity | Formula |
|---|---|
| Modularity (per community) | Q = Σ_c [ℓ_c/m − (d_c/2m)²] |
| Modularity (matrix) | Q = (1/2m) Σ_ij (A_ij − k_i k_j/2m) δ(c_i,c_j) |
| Merge gain | ΔQ = ℓ_ab/m − 2(d_a/2m)(d_b/2m) |
| One community | Q = 0 |
| All singletons | Q = −Σ_i (k_i/2m)² |
| Entropy of a partition | H = −Σ_x (n_x/n) log(n_x/n) |
| Mutual information | I = Σ_x,y (n_xy/n) log[n·n_xy/(n_x n_y)] |
| NMI | 2I / (H_1 + H_2) |
| Girvan–Newman cost | O(m²n) |
| Edge betweenness | # shortest paths (all pairs) running along the link; ties split 1/# tied paths |
| Bridge between groups of sizes n_A, n_B (single bridge) | carries n_A·n_B shortest paths |
| Merge gain, hand form | ΔQ = [4m·ℓ_ab − 2 d_a d_b] / (2m)² |
| Sanity check | Σ_c d_c = 2m |
| Resolution limit (Goodies — not on test) | modularity merges communities with fewer than ~√(2m) internal links |
| k-clique edge count | k(k−1)/2 |
| Adjacent k-cliques | share k−1 nodes |
| Link similarity (link communities) | Jaccard of endpoints' inclusive neighborhoods: size(N⁺(i) ∩ N⁺(j)) / size(N⁺(i) ∪ N⁺(j)) |
| Partition density | D = (2/M) Σ_c m_c · [m_c − (n_c−1)] / [(n_c−2)(n_c−1)] |
| Strength | s_i = Σ_j w_ij |
| Weighted link length | ℓ_ij = 1/w_ij (strong tie = short) → shortest path with Dijkstra |
| Weighted modularity | same Q with A_ij → w_ij, k_i → s_i, m → total weight W |
| Weight share of a link | p_ij = w_ij / s_i |
| Disparity filter (significant for i) | (1 − p_ij)^(k_i − 1) < α ; keep link if significant at **either** end |
| Global threshold | keep link iff w_ij ≥ θ |

---
*Updated 2026-09-24 — Full pass against all four week pages on the course site. Week 1: added
the representation-choice concept, the in/out-degree-equality fact, the full worked Marvel
example (n, m, density, isolates, giant component), and data-vs-decoration notes on drawings.
Week 2: added the Marvel clustering shuffle-test numbers (mean 0.155, SD 0.009, z≈18), the
Watts–Strogatz q≈0.2 match to Marvel, reciprocity as a null-model trap, and the friendship-
paradox Marvel numbers. Week 3: added the Medici story, Krackhardt's kite, the Marvel path/
degree/closeness/betweenness/PageRank worked examples, both AI-flaw sentences, rank
correlations, and the assortativity reference values + rewiring extremes. Week 4: added the
Zachary karate club story, the full k-clique-community definition + table, the full link-
community definition + overlap paradox, the full weights/strength section with worked
examples, the full backbone section (global threshold + disparity filter worked example +
α table), and the five drawing rules written out in full (previously only formula-box
entries). Nothing here is missing anymore relative to the site's weeks 1–4 as of this date —
if the professor updates a week page before the test, re-check that week specifically.
**Test 1: Wed 30 Sep, 08:30–09:30 (arrive 08:10), building 303A, Auditorium 42 or 43 (email
will confirm) — Weeks 1–4, closed book, 16 MC + 4 short written; every formula needed is
printed on the test paper, you are never asked to write one from memory.***
