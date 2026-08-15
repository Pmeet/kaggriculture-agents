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
