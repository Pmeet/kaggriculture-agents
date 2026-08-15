# Approach Audit — 2026-08-15

An external brief framed the competition as operations research and industrial
organisation, and listed the concepts that should decide it. This document maps
every named concept onto what this repository has actually built, measured, or
rejected, and sets the plan for the next round of work. Read with `AGENTS.md`,
which holds the evidence behind each verdict.

## Scoreboard

Twenty-one distinct concepts named in the brief. **12 implemented, 4 partial,
5 untried.** Separately, 7 ideas were tried and rejected on measurement — the
category the brief cannot see, and the one that saves the most time.

### Implemented, with measurements behind them

| concept | where it lives |
| --- | --- |
| Payback / ROIC purchase ranking | one budget in `plan_purchases`, "spent strictly in payback order" |
| Turnpike / non-stationary policy | phase-switched assignment plans (`ggrr`/`grrn`), last-day gates, endgame ramp |
| Marginal revenue product vs wage | hiring prices the next hand's fib cost against jobs it can still reach (+$18k over the clock window) |
| Price impact / optimal execution | `sellable_quantity` stops each product at its collapse point; `max_price_impact` cap; impact-ranked sell slots (queue position measured at ~11%) |
| Demand elasticity → specialise vs diversify | `tile_alloc: "marginal"` — each tile priced at declining marginal value; melon keeps tiles until its marginal value crosses carrot's |
| Action economy | every job valued in dollars per action; `marginal_action_cost` prices an action at the marginal job dropped — a shadow price on labour |
| Knapsack-style greedy baseline | the shipped agent, 19 versions deep |
| Engine constants extracted | `lab/economics.py`; `price_at` replicates the engine's curve exactly; engine-version forensics from live replays |
| Fast harness, paired evaluation | `arena.fast_play` (>2× via skipping the per-step deep copy), paired seeds from both seats, 40-seed floor, common random numbers |
| Economics before code | `lab/economics.py` is the spreadsheet |
| Rule-based greedy before search | the whole project so far |
| Endgame liquidation cutoff | `endgame_relax_days` ramp in `plan_sales`; nothing unsold at the final step is a submission gate |

### Partial

| concept | what exists | what's missing |
| --- | --- | --- |
| Cournot / opponent supply | `rival_incoming` reads the opponent's committed tiles and sells ahead of their harvest landing | no best-response quantity planning; reaction is sell-side only |
| Shadow prices / bottleneck switching | labour is priced; cash via proportional reserves; land via the capacity-slack gate; the gate-firing audit counts which constraint binds | no unified "spend only on the binding constraint" dispatcher |
| Scheduling / production levelling | four assignment strategies measured, phase-switched; idle unit-turns tracked (3,058 → 1,359) | no deliberate planting stagger to smooth harvest labour; Little's Law unused |
| Replay mining | `lab/replay.py` forensics on individual downloaded replays; the THUNDER table in `AGENTS.md` came from it | no bulk regression of final bank on early-choice features across the public replay dataset |

### Tried, measured, rejected — do not re-litigate without new data

| idea | verdict |
| --- | --- |
| Hungarian optimal assignment | provably better matching, **-$25,078** a game; the per-turn objective is what's wrong |
| Rate (per-turn-committed) pricing throughout | `rrrr` **-$40,732**; correct only late (`ggrr` ships) |
| Horizon pricing, linear share | -$1.8k to -$4.2k, off by default; the lumpy per-day version remains open (see plan) |
| Cash cushion before building pens | **-$34,382**; an empty pen is an option, not waste |
| Capping / pacing melon | costs $17-30k; settled twice |
| Pure-value hiring test | -$15k; workload x price is the rule |
| Flat cash reserves | regime-dependent; proportional `scaled_reserve` replaced them |

Local Elo was also consciously not adopted: paired bank margin on common seeds
is lower-variance than win-rate-derived ratings at these sample sizes.

### Untried

1. **Cournot best-response quantity planning** — choosing *production*, not just
   sale timing, against the opponent's visible commitments.
2. **Deliberate price depression** of a crop the opponent is heavily committed to.
3. **Cobweb dynamics** — planting against predictable price oscillation.
4. **Rolling-horizon MPC with an LP/MIP.** Constrained: the submission must be
   stdlib-only, so OR-Tools/PuLP cannot ship. An LP can only run offline to
   derive policies, or be hand-rolled.
5. **Beam search / Monte Carlo rollouts.** Latency budget is 1s/turn; we use
   ~0.6ms. Enormous headroom, but requires a forward model of the engine inside
   the agent. `ROADMAP.md` lists it as a later-phase item.

## Constraints that shape what is viable

- `main.py` must stay **self-contained and standard-library-only**, with
  `agent` the last module-level callable. No solver libraries in the agent.
- Runtime is offline and CPU-only; 1s/turn budget, ~0.6ms used.
- The Kaggle access token lives only on the owner's WSL machine. The cloud
  container (rebuilt 2026-08-15: `~/.venvs/kaggri`, Python 3.12 via uv,
  `kaggle-environments==1.32.6`, 104 tests green, ruff clean, full diagnostic
  episode verified) can measure but **cannot** download replays or read the
  leaderboard.

## The plan

Ordered by expected value, each step gated by the measurement discipline in
`AGENTS.md` (40-seed floor, held-out seeds, phase tables, both benchmarks).

1. **Per-day supply/demand ledger** — the rolling-horizon replanner, stdlib
   edition. Every planted tile already carries the date its harvest lands; walk
   the tiles (ours and the rival's) and accumulate a per-day, per-product
   supply/demand projection, then price plantings and sales against the day
   they actually trade. This is the correct version of the rejected linear
   horizon share, the mechanism for the wheat gap (we sell 28 a game, the
   leaders 433 — the largest single line item), and the Cournot quantity
   response in practical form.
2. **Reactive planting** — hold a measured fraction of planting capacity until
   the actual shop draw lands (day 3+) instead of spending it all on the pool
   prior. Directly targets the ladder left tail: a third of real games go wrong
   in a way no local game does, and the unlucky-draw hypothesis is the first
   one to test.
3. **Endgame precision pass** — 39% of ladder games are decided by under $10k,
   so the rating lever is close games, not mean margin. Enumerate/beam the last
   1-2 days exactly (final sales, last placements, stranded stock) inside the
   latency headroom. First search foothold, smallest state space.
4. **A real opponent for the pool** — reconstruct the 3,200-rated archetype
   (strawberry+wheat at scale over 13 animals) from replay forensics. Every
   current opponent is our own descendant; the next tuning round needs a foil
   or it fits ourselves again.
5. **Replay meta-dataset regression** — regress final bank on early-choice
   features (first land day, hires, per-crop plant counts) across the public
   replays. Needs the token, so it runs on the owner's machine.
6. **Market-attack experiments** — best-response quantity shading and
   deliberate dumping against rival commitments, built on the ledger from
   step 1. Cheap to test once the ledger exists; unproven value, so it waits
   its turn.
7. **Joint re-tune after every structural change** — `lab/evolve.py`; the plan
   and the weights are one decision. Upgrading the search itself (CMA-ES) is
   optional and lower value than what it would tune.

Steps 1-3 are the new approach. They replace one-shot prior-based forecasting
with day-granular replanning, and mean margin with close-game conversion — the
two places the ladder says the current agent actually loses.

## Step 1 log: the per-day ledger (2026-08-15)

Built and measured. **It does not beat the shipped pricing, and it is off by
default.** What follows is the record so the next attempt starts here rather
than at the beginning.

### What was built

`market_ledger` walks both farms' tiles and accumulates each committed block of
production on the day it lands, against the town's per-day drain (unlocked
shops as they are, future unlocks at the pool average). `ledger_crop_revenue`
then prices each yield of a candidate planting at the projected inventory on
its own landing day, and `animal_profit` does the same per production tick.
Behind `ledger_pricing`, `ledger_chain`, `ledger_animals`, plus two weights.

### The measurements

40 seeds a side against both benchmarks, search and held out:

| variant | search | holdout | margin (holdout) |
| --- | --- | --- | --- |
| **control (shipped)** | **0.875** | **0.825** | **+$8,738** |
| ledger, crops only | 0.494 | 0.381 | -$3,781 |
| ledger, crops + animals | 0.463 | 0.362 | -$3,492 |

Two traps this walked into, both already documented here and both worth
re-reading before the next structural change:

* **Eight seeds decided nothing.** The same crops+animals variant measured
  **+$2,770 held out over 8 seeds** and -$3,492 over 40. The 40-seed floor in
  `AGENTS.md` is not conservatism, it is the minimum that distinguishes a
  finding from a draw.
* **A measurement was discarded, not reported.** `main.py` was edited while a
  40-seed run was in flight; `lab/arena.run_match` builds a fresh process pool
  per call, so later workers import the edited file and arms end up measured
  against different code. That run was killed and re-run clean. **Do not touch
  `main.py` while a harness run is going.**

### Why it lost, as far as it was diagnosed

The phase table (20 seeds vs `baseline_l`) says the loss is everywhere and
worst at the end:

| phase | control | ledger |
| --- | --- | --- |
| day 0-10 | +$494 | +$27 |
| day 10-20 | +$5,839 | +$3,670 |
| day 20-30 | +$5,476 | **-$1,784** |

At day 30 the ledger stands on 29 crops to control's 20 and 25 empty tiles to
control's 39: it keeps committing tiles late that cannot pay back. Two
mechanisms are implicated, and neither is disproven yet.

1. **The dated model is honest about a harvest and blind to the replant.** A
   wheat tile frees on day 4 and goes again; single-cycle dated pricing books
   only the first harvest, which unpriced the short-crop opening completely
   (first naive run: 0.000, -$40k). `ledger_chain` prices the tile as the chain
   of plantings it enables and restores the opening — day-0 wheat job value
   -24 to +30 on a synthetic board, and a trace showing 19 wheat tiles by day 2
   and a wheat line all season, which is the leaders' shape. It is a large
   improvement over naive and still short of control.
2. **Every dollar-denominated constant is fitted to the old scale.** Chain
   pricing roughly doubles crop values and the ledger raises a day-0 cow from
   $2,840 to $7,913; `plant_commitment_cost`, `land_weight`, `job_weight`, the
   action-cost floor and cap, and the hard `max(50.0, ...)` job floors were all
   fitted against season-total pricing. Only two were hand-tuned here.

The strongest single clue is `town_pull_weight`, which the joint search settled
at **0.1** — the shipped agent believes a tenth of the projected town drain.
The ledger was built believing all of it (`ledger_drain_weight` 1.0) and was
only ever swept upward, where it got worse. Sweeping it down is the obvious
missing experiment, and `lab/evolve.py` now takes `--start` and grows the two
ledger weights into its search space so the whole set can be re-fitted jointly
— which is what `AGENTS.md` says a structural change requires, and what turned
the shop-led economy from -$4,011 into +$2,161 the last time.

### Verdict: not adopted

The re-fitting hypothesis was tested and was not enough. Joint search from a
ledger start, then all three arms at 40 seeds against the benchmarks:

| arm | search | holdout | margin |
| --- | --- | --- | --- |
| **control (shipped)** | **0.875** | **0.825** | **+$8,738** |
| evolved params, ledger **off** | 0.044 | 0.037 | -$21,467 |
| evolved params, ledger **on** | 0.619 | 0.594 | +$5,609 |

The ablation is the interesting row: the evolved parameters are catastrophic
*without* the ledger, so they are not a general improvement — the ledger is
worth +$27,076 to its own co-fitted set. The model does real work. It just does
not beat the shipped agent, falling $3,129 and 0.23 win rate short after four
hand-tuned weights and a joint search.

Ledger pricing stays **off**, and `main.py` ships unchanged. Effort moves to
steps 2 and 3, where the ladder evidence is stronger than anything local.

Its own search overfit its pool — +$14,600 held out against `baseline_j` and
`baseline_b`, +$5,609 against the benchmarks. Re-running the search against the
benchmarks would fit what we validate on, so it was not done.

### Also fixed along the way

`animal_profit` priced fertilizer and feed at a flat season price. Fertilizer
falls from about $100 to $30 across a season while wheat climbs, so the flat
price overstated the dung and understated the feed. Only active in ledger mode
at present; worth porting to the shipped model as a change in its own right.
