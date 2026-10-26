---
Course: 02805 Social Graphs and Interactions (DTU, Fall 2026)
Source: https://sunelehmann.com/socialgraphs2026-web/weeks/week3.html
Textbook: Michele Coscia, The Atlas for the Aspiring Network Scientist, 2nd ed. (networkatlas.eu)
Status: page fetched 2026-09-13. Exercises 3.1-3.12 resolvidos em exercises/week3/3.1-3.12_who_matters_and_why.ipynb.
---
# Week 3 — Who Matters, and Why

Study notes: a resume of the Week 3 course page, cross-referenced with the matching textbook
chapters. No companion notebook started yet — create
`../exercises/week3/` when you begin 3.3/3.5/3.7 (the code exercises).

## 0 · Framing

"This week we describe more network measures that show the many ways real networks are
different from random ones." Distances come from one algorithm (breadth-first search);
centrality measures give many different answers to "who matters?"; and, as in Week 2, a
centrality value only means something once it's compared to the right null model.

## 1 · Who matters?

Centrality is a toolbox, not a single number — each tool answers one specific question well:

- **Degree centrality** — how many direct connections?
- **Closeness centrality** — how quickly can you reach everyone?
- **Betweenness centrality** — how often are you a bridge others must cross?
- **Eigenvector / PageRank centrality** — are you connected to other important nodes?

Picking the right one for a question (not just reaching for degree by default) is the recurring
skill this week trains.

## 2 · Paths, distances, and breadth-first search

**Definitions**

- **Walk** — any sequence of linked nodes (can repeat nodes/edges).
- **Path** — a walk that never repeats a node.
- **Distance** $`d_{ij}`$ — the length of the *shortest* path between $`i`$ and $`j`$; $`\infty`$ if
  unreachable.
- **Breadth-first search (BFS)** — expand outward from a start node ring by ring (all distance-1
  nodes, then all new distance-2 nodes, ...); the ring a node first appears in *is* its distance
  from the start. $O(n+m)$.
- **Eccentricity** of a node — its distance to the farthest node. **Diameter** — the largest
  eccentricity in the network. **Radius** — the smallest. **Center** — node(s) at the radius.

**Marvel numbers:** average path length 2.67, diameter 6, 86% of character pairs are 2–3 steps
apart.

**Directed networks — reachability splits in two:**

- **Weakly connected** — connected once you ignore edge direction.
- **Strongly connected** — every node can reach every other node *following the arrows*.
- Marvel's largest strongly connected component holds 229 of 303 characters — direction matters,
  since links (Wikipedia mentions) aren't reciprocal: $`d_{AB}`$ can differ from $`d_{BA}`$, and
  either can be $`\infty`$ while the other is finite.

**Textbook:** Atlas Ch. 10 *Paths & Walks* (§10.1, §10.4) for the definitions above; Ch. 13
*Shortest Paths* (§13.1–13.3) for BFS and its correctness/complexity.

## 3 · Degree and closeness centrality

**Degree centrality** $`k_i`$ — purely local, never looks past a node's direct neighbors.
Directed networks split it into **in-degree** and **out-degree**, which can tell very different
stories: Spider-Man has 106 in-links (widely mentioned); the Hulk has 64 in-links but only 10
out-links (mentions few others).

**Closeness centrality:**

$$
C_i^{\text{close}} = \frac{n-1}{\sum_{j \ne i} d_{ij}}
$$

Higher closeness = shorter average distance to everyone else, i.e. better reach. **Problem:** if
even one node is unreachable, $`\sum_j d_{ij} = \infty`$ and closeness collapses to 0 — unusable
on disconnected or many directed networks.

**Harmonic centrality (the fix):**

$$
C_i^{\text{harm}} = \frac{1}{n-1}\sum_{j \ne i} \frac{1}{d_{ij}}, \qquad \left(\frac{1}{\infty}=0\right)
$$

Unreachable nodes just contribute 0 to the sum instead of breaking it — works cleanly on
directed and disconnected networks.

**Textbook:** Atlas Ch. 14 *Node Ranking* covers degree/closeness/betweenness/eigenvector/
PageRank across §14.1–14.6 (the page doesn't break down which subsection maps to which measure,
but the order matches this page's own).

## 4 · Betweenness centrality: the broker

$$
b_i = \sum_{s \ne i \ne t} \frac{\sigma_{st}(i)}{\sigma_{st}}
$$

where $`\sigma_{st}`$ = number of shortest paths from $`s`$ to $`t`$, and $`\sigma_{st}(i)`$ =
how many of those pass through $`i`$.

**The Medici story:** in 15th-century Florence, the Medici didn't control the city by having the
most marriage ties — they controlled it because more than half of all shortest paths between the
*other* families ran through them. Betweenness measures **control** via structural position, not
popularity.

**Properties:**

- Can be **high at low degree** — a node can be the sole gateway to a whole region of the
  network.
- Can be **near zero at high degree** — if a node's many neighbors are all linked to each other
  anyway, none of them need to go *through* it.
- Identifies **brokers**, **bridges**, **bottlenecks**.

## 5 · Eigenvector centrality and PageRank

**Eigenvector centrality:**

$$
x_i = \frac{1}{\lambda}\sum_j A_{ij}\,x_j
$$

A node is important if it's connected to important nodes — circular by design, solved by power
iteration: replace every score with the sum of its neighbors' scores, rescale, repeat until it
converges.

**PageRank (built for directed networks):**

$$
\mathrm{PR}_i = \frac{1-\alpha}{n} + \alpha \sum_{j \to i} \frac{\mathrm{PR}_j}{k_j^{\text{out}}}
$$

Models a random surfer clicking links, who teleports to a uniformly random page with probability
$`1-\alpha`$ (convention: $`\alpha = 0.85`$). Teleportation fixes what plain eigenvector
centrality can't handle on directed networks: dangling nodes (no out-links) and score getting
trapped inside strongly connected components. A link from a page that links to *few* others is
worth more than a link from a page that links to *many* — out-degree splits the vote.

**Random-walk view:** on an *undirected* network, the walk's stationary distribution is just
proportional to degree, $`\pi_i = k_i / 2m`$ — no teleportation needed there.

**Textbook:** Atlas Ch. 11 *Random Walks* (§11.1, §11.3, §11.4) for the random-walk/PageRank
connection.

## 6 · Compared to what? (null models matter)

Same discipline as Week 2: a centrality value means nothing until it's compared to a
degree-preserving shuffle.

- **Spider-Man's betweenness:** real value 23% of all shortest paths; degree-preserving-shuffle
  average also ≈23%. **Not a finding** — it's entirely explained by his degree.
- **Hercules:** 26 links, real betweenness 0.037 vs. 0.018 shuffled → a genuine broker.
- **Black Widow:** 25 links, real betweenness ≈2× the shuffled value → genuine structural
  position, not just link count.
- **Black Cat:** 28 links, real betweenness only ⅓ of what her degree predicts → she's
  "sheltered" — her neighbors mostly link to each other, so she isn't needed as a bridge.

**Two habits for reporting any centrality number:**

1. State plainly which question the measure answers.
2. Compare against the right null model (degree-preserving shuffle is the standard one here).

## 7 · Mixing patterns: degree assortativity

**Degree assortativity** $`r`$ — the Pearson correlation between the degrees at the two ends of
every edge.

- $`r > 0`$: **assortative** — hubs tend to link to hubs (typical of social networks).
- $`r < 0`$: **disassortative** — hubs tend to link to low-degree nodes (typical of technological
  and biological networks).

**Marvel:** real $`r = -0.105`$; degree-preserving shuffle gives $`r = -0.118 \pm 0.009`$. The
real value sits *inside* the shuffled distribution → Marvel is not significantly disassortative;
its mild disassortativity is exactly what its degree distribution forces on its own
(**structural disassortativity**), not a separate wiring effect.

**Average neighbor degree** $`k_{nn}(k)`$ — the mean degree of the neighbors of nodes with
degree $`k`$:

- Rising with $`k`$ → assortative.
- Falling with $`k`$ → disassortative.
- Flat at $`\langle k^2\rangle/\langle k\rangle`$ → no mixing pattern (matches a random/
  degree-preserving-shuffle baseline).

**Homophily** — assortative mixing by an *attribute* (team, decade, ...) rather than by degree.
Tested by shuffling attribute labels across nodes while keeping the network structure fixed
(label permutation, not edge rewiring).

**Textbook:** Atlas Ch. 31 *Quantitative Assortativity* (§31.1, §31.2) for $`r`$ and
$`k_{nn}(k)`$; Ch. 30 *Homophily* (§30.2) for attribute mixing.

## 8 · Cliques

**Definitions**

- **Clique** — a set of nodes where every pair is linked.
- **Maximal clique** — a clique no node can be added to.
- **Clique number** — the size of the network's largest clique.
- A $`k`$-clique contains $`k(k-1)/2`$ edges (every pair, by definition).

**Marvel facts:** 1,835 triangles (3-cliques); 477 5-cliques; clique number **8** — Betsy
Braddock, Cable, Cyclops, Emma Frost, Jean Grey, Northstar, Rachel Summers, Wolverine, all X-Men.

**Textbook:** Atlas Ch. 12 *Density* (§12.3) connects clique density back to the network-density
ideas from Week 1–2.

## Quick formula box

| Quantity                                  | Formula                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Closeness centrality                      | $`C_i^{\text{close}} = (n-1)/\sum_{j\ne i} d_{ij}`$                                            |
| Harmonic centrality                       | $`C_i^{\text{harm}} = \frac{1}{n-1}\sum_{j\ne i} 1/d_{ij}`$                                    |
| Betweenness centrality                    | $`b_i = \sum_{s\ne i\ne t} \sigma_{st}(i)/\sigma_{st}`$                                        |
| Eigenvector centrality                    | $`x_i = \lambda^{-1}\sum_j A_{ij}x_j`$                                                         |
| PageRank                                  | $`\mathrm{PR}_i = (1-\alpha)/n + \alpha\sum_{j\to i}\mathrm{PR}_j/k_j^{\text{out}}`$ (α=0.85) |
| Random-walk stationary dist. (undirected) | $`\pi_i = k_i/2m`$                                                                             |
| Degree assortativity                      | $`r`$ = Pearson corr. of degree at edge endpoints                                              |
| Average neighbor degree                   | $`k_{nn}(k)`$ = mean neighbor degree of degree-$`k`$ nodes                                   |
| $`k`$-clique edge count                 | $`k(k-1)/2`$                                                                                   |

## Which centrality for which question? (Essentials skill)

| Question                                             | Measure                |
| ---------------------------------------------------- | ---------------------- |
| Who has the most direct contacts?                    | Degree                 |
| Who can spread something to everyone fastest?        | Closeness / harmonic   |
| Whose removal disconnects/reroutes the most traffic? | Betweenness            |
| Who is well-connected*to well-connected people*?   | Eigenvector / PageRank |
| Vaccination priority (contact count)                 | Degree                 |
| Retirement impact on the org                         | Betweenness            |
| Friend-count style question                          | Degree                 |
| Airport closure delaying the most itineraries        | Betweenness            |

## Exercise index (this week's page)

- **3.1** — Did you really read it? — paths 🧠
- **3.2** — BFS by hand 🧠
- **3.3** — Distances on Marvel, as code 🔬
- **3.4** — Centrality by hand 🧠
- **3.5** — Centralities on Marvel 🔬
- **3.6** — PageRank by hand 🧠
- **3.7** — PageRank on Marvel 🔬
- **3.8** — Brokers, compared to what 🧠+🔬
- **3.9** — Mixing, compared to what 🧠+🔬
- **3.10** — Cliques by hand 🧠
- **3.11** — Ship an explorable 🚀 *(stretch/optional)*
- **3.12** — Go nuts with your LLM 🚀 *(weekly group post)*

Not started yet — none of 3.1–3.12 has been attempted this session.

## Goodies (advanced, not required for the test)

**Brandes' algorithm for betweenness** — one BFS per source suffices, giving $`O(nm)`$ instead of
brute-forcing every pair's shortest paths: count paths $`\sigma_{sv}`$ forward through the BFS
tree, then accumulate dependency $`\delta_s(v) = \sum_{w} \frac{\sigma_{sv}}{\sigma_{sw}}(1+\delta_s(w))`$
backward, ring by ring.

**Eigenvector centrality, PageRank, and Google's rise** — the full story behind §5: plain
eigenvector centrality fails on directed networks (rank sinks trap all the score); row-normalizing
the adjacency matrix (each out-link becomes an equal share of one "vote") fixes dangling nodes;
adding teleportation with probability $`1-\alpha`$ guarantees a unique positive stationary
distribution on *any* network — that combination is the actual Google matrix. A **link-farm
attack** (a clique of 26 fabricated pages) can push an unlinked page to rank #1 under plain
eigenvector centrality; PageRank keeps it around rank 99 because votes still have to be split.
Relatives: **Katz centrality** (scores all walks with exponential decay $`\beta^\ell`$; works on
directed networks) and **HITS** (separate hub/authority scores).

**Rich club coefficient** — density of links *among* the highest-degree nodes, normalized against
a degree-preserving shuffle; a ratio above 1 means hubs are more tightly interconnected than their
degrees alone require.

**Degree-assortativity bounds** — these are structural, not algorithmic, limits: Spider-Man's 106
links inside a 277-node network caps how assortative Marvel *could* even look (~+0.17 ceiling —
there simply aren't enough other hubs to pair him with); the disassortative floor sits near −0.53
(from greedily pairing the biggest stubs with the smallest ones). Truncating the single largest
hub sharply raises the assortative ceiling. **Degree-stratified permutation** — shuffle attribute
labels only *within* degree bins, to isolate homophily from pure popularity effects.

**Random-walk concepts (beyond PageRank):** **hitting time** $`H_{ij}`$ = expected steps from
$`i`$ to $`j`$ (not symmetric); **commute time** $`H_{ij}+H_{ji}`$ = $`2m`$ × the pair's effective
electrical resistance. Foundational for the node-embedding methods coming in Week 7.

**Interactive explorables referenced:** bfs-wavefront, centrality-anatomy, random-walker,
centrality-scatter, mixing-dial, clique-hunt.
