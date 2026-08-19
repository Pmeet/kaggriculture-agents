# Problem: The Idle Farmhands

*A scheduling problem taken from a live Kaggle simulation competition. All
figures below are measured from real games, not invented. If you solve this well,
it is worth roughly a 30% increase in work done per game.*

---

## Background

You control a crew of workers on a square grid farm. Every worker gets exactly
one action per turn. Jobs appear on tiles and pay money. Our current scheduler
spends **56% of all actions walking** and only **31% doing work**. The best
players in the competition spend **42% walking and 41% working** from the same
budget — they complete **49% more jobs per game** with the same number of
actions.

We want to know how they do it, or at least what the right algorithm is.

---

## Formal statement

### The board

- A `10 x 10` grid. Tiles are `(x, y)` with `0 <= x, y < 10`.
- The centre four tiles `(4,4), (5,4), (4,5), (5,5)` are the **depot**.
- Movement is 4-directional. One move = one tile = one turn. Distance between
  two tiles is Manhattan distance. There are **no obstacles**: every tile is
  passable and multiple workers may occupy the same tile.
- Typically **75 of the 100 tiles** are in play.

### Time

- The game is **30 days** of **24 turns** each: `T = 720` turns total.
- At the start of each day **every worker is teleported to tile `(4,4)`**, the
  depot. Days are therefore near-independent routing problems that all start
  from the same point.

### Workers

- `k` workers, where `k` grows over the game and is typically **12–13**.
- Each turn, each worker independently does exactly one of:
  - `MOVE` one tile north/south/east/west;
  - `WORK` — complete one job on the tile it currently stands on;
  - `IDLE`.

### Jobs

At the start of every turn you are given the set of **currently available jobs**.
Each job `j` has:

- a tile `p_j`;
- a value `v_j > 0`, paid in full if a worker completes it;
- jobs are completed in **one** `WORK` action by a worker standing on `p_j`;
- each job may be completed **at most once**.

Measured distribution, per turn, from real games:

| quantity | p10 | median | p90 | max |
|---|---|---|---|---|
| jobs available | 2 | **35** | 77 | 117 |
| distinct tiles holding a job | — | **24** | 55 | 68 |
| job value `v_j` | \$9 | **\$84** | \$650 | \$10,038 |

So there are typically **~2.9 available jobs per worker per turn** — the crew is
oversubscribed and most jobs will never be done. Choosing *which* to skip is the
whole problem.

### Job dynamics — the part that matters

Jobs are **not** adversarial and **not** uniformly random. They arise from farm
state that evolves on a **known schedule**:

- A crop planted on day `d` needs watering on specific days, and becomes
  harvestable on a specific day. Both are deterministic functions of `d` and the
  crop type.
- An animal produces on a fixed interval and needs feeding **every** day. Each
  animal generates up to 4 distinct jobs per day, all on **the same tile**.
- A job that is not done today may still be available tomorrow, or may **expire**
  (a crop left unwatered dies; a ripe crop rots after a few days).

**Consequently: at dawn, most of the day's job set is already predictable.** You
know which tiles will need watering, which animals need feeding, and roughly what
each will pay. New information arriving mid-day is real but a minority.

### Objective

Maximise total value collected over `T = 720` turns.

### Compute budget

**1000 ms per turn**, single-threaded. Our current scheduler uses 0.7 ms, so
there is around three orders of magnitude of headroom. Pure algorithm, no
external libraries.

---

## The baseline to beat

Each turn we build the job list, then run a **greedy maximum-weight matching**
between workers and jobs, scoring each `(worker, job)` pair as:

```
score(w, j) = v_j - dist(pos_w, p_j) * C
```

where `C` is the estimated opportunity cost of one turn, computed as the value of
the marginal job we expect to drop for lack of capacity. Pairs are sorted by
score; each worker takes its best still-unclaimed job; a worker with no positive
pair walks toward the nearest unclaimed job.

**This is recomputed from scratch every turn, with no memory of the previous
turn's assignment.**

Measured performance:

| | ours | best competitor | best in field |
|---|---|---|---|
| moving | 55.6% | 42.3% | 42.3% |
| idle | 16.9% | 16.5% | 9.4% |
| **working** | **30.7%** | **41.2%** | **42.6%** |
| tiles walked per job done | **1.87** | **1.02** | **1.02** |

---

## What we have already tried, and measured as worse

Please do not propose these; they are ruled out empirically.

1. **Raising `C`** (making walking more expensive). Strictly worse at every
   setting tested — win rate 0.64 → 0.08 at 1.5×, → 0.02 at 2×.
2. **Bonusing jobs on the tile a worker already stands on**, to encourage
   clearing a tile before moving. Moves the targeted metric convincingly (walk
   per animal-tile job 1.47 → 0.73) and **loses money**, because total travel is
   roughly conserved — chaining only changes *which* job gets the free slot, and
   it picks the cheaper one.
3. **Doing an unclaimed job while passing through a tile en route.** Worse.
4. **Optimal assignment instead of greedy.** We solved the per-turn matching
   exactly (verified against brute force, never worse than greedy, +\$12,421 of
   assigned job value per game) and the agent got **\$25,078 worse**. The
   per-turn objective is what is wrong, not the solver.

Item 4 is the strongest hint available: **the myopic objective is the defect.**
A per-turn optimum does not compose into a good day.

---

## Questions

Answer whichever you can; partial answers are useful.

1. **Formalise it.** What is this problem, precisely? Name the closest studied
   variant and its known hardness and approximability.

2. **Why does per-turn optimal assignment lose to per-turn greedy?** Give the
   mechanism, ideally with a small concrete instance where greedy beats the
   per-turn optimum over a horizon.

3. **What is the right objective?** The scoring function `v_j - dist * C` prices
   the walk *to* a job but nothing about where the worker ends up. Propose a
   per-turn score, or a planning formulation, that accounts for continuation
   value. Be explicit about what must be estimated and how.

4. **Give an algorithm** that fits 1000 ms/turn and beats the baseline. Concrete
   enough to implement. State its complexity in `k` (workers), `n` (jobs) and the
   planning horizon `H`.

5. **What is the theoretical ceiling?** With 12 workers, 24 turns, all starting
   co-located at the centre of a 10×10 grid, and ~35 jobs available per turn:
   what is the maximum achievable work fraction? Is 41% (the best observed)
   near-optimal, or is the real ceiling much higher?

6. **Territories.** Does partitioning the board into per-worker regions help
   here, given all workers start co-located each day and the job distribution is
   uneven and shifts over the 30 days? If so, how should the partition be chosen
   and how often re-chosen?

---

## Notes for the solver

- Workers are **interchangeable** — no skills, no capacity limits.
- Workers may **share a tile**; there is no collision constraint.
- A worker carrying goods must occasionally return to the depot, but that is a
  minority of traffic and can be ignored at first pass.
- The value distribution is heavy-tailed: median \$84, p90 \$650, max \$10,038.
  A few jobs matter enormously and most are near-worthless. Any answer that
  treats jobs as interchangeable will underperform.
- Roughly **a third of all work** is on animal tiles, which carry up to 4 jobs
  each per day on a single tile — a natural clustering the baseline does not
  exploit.
- The opponent plays a separate, identical farm; the two interact only through
  shared market prices. **You may ignore the opponent entirely.**
