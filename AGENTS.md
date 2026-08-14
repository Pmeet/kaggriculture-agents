# Kaggriculture Agent Handoff

Last updated: 2026-08-12 (Asia/Calcutta)

Durable handoff for any agent continuing this work. Read with `README.md` and
`ROADMAP.md`.

## Non-negotiable constraints

- The user granted **standing authority to submit** on 2026-08-07 ("don't need to
  ask me for submissions if you decide it's worth it"). Judgement still applies:
  five slots a day, only the latest two stay active, so submit when local
  evidence says a candidate beats the live one.
- The 2026-08-11 hold was lifted on 2026-08-12 ("add our first submission for
  today") and v15 went up. The live constraint now is the two-active-slots rule:
  see "Live submissions" below before uploading anything.
- Never print, commit, or expose the Kaggle access token. It lives at
  `~/.kaggle/access_token` (mode 600) in WSL and is scoped per command via
  `KAGGLE_API_TOKEN="$(cat ~/.kaggle/access_token)"`.
- Competition downloads are restricted material. Keep `competition-data/`,
  `replays/`, `logs/`, `reports/`, `.venv/` and `submission*.tar.gz` out of Git.
- `main.py` must stay a self-contained, standard-library-only Kaggle entrypoint,
  and `agent` must remain the **last** module-level callable: the loader takes
  `[v for v in namespace.values() if callable(v)][-1]`. Anything callable defined
  after it — including a class — silently becomes the submitted agent.
- The runtime is offline and CPU-only.

## Where things stand

`main.py` is a livestock-led economy with a crop economy grown against
forecast town demand. Against the pool it banks $79k-$102k; the gauntlet sits
at MEAN 0.997 / WORST 0.979.

**The local pool is saturated and no longer measures anything.** Every opponent
in it is a descendant of our own ideas, and we score 1.000 against nearly all of
them. Steer on head-to-head paired bank margin against the last frozen snapshot
(`agents/baseline_i.py`, via `lab/ab.py`), and on the ladder.

### The ladder is the only honest signal, and it says we are mid-pack

Read on 2026-08-11 from the live API. **Rank 1929 of 3809; rating 717.7 against
a median of 726.9 and a leader at 3192.8.** Matchmaking pairs us with agents
rated 437-924, and across the 52 completed games of our two live submissions we
are **28-24 (0.54)**. Our banks in those games run $24k-$121k -- a left tail that
never appears locally, where the same agent banks a tight $76-93k.

So: local score ~1.0, ladder score ~0.54. Trust the ladder.

### What the 3,200-rated agents actually do

From replay 91537598 (THUNDER THUNDER, rank 1, vs HealthStone; both ~3,200),
laid against our own game in the same format:

| | THUNDER | HealthStone | us (2026-08-11) |
| --- | --- | --- | --- |
| final bank | 137,003 | 128,119 | 63,750 |
| strawberry sold | 272 | 263 | 52 |
| wheat sold | 433 | 431 | 27 |
| milk sold | 250 | 233 | 231 |
| fertilizer sold | 257 | 232 | 220 |
| melon sold | 108 | 104 | 102 |
| WATER actions | 998 | 875 | 294 |
| idle (PASS) unit-turns | 1,156 | 644 | 3,058 |
| animals | 9 cow, 4 sheep | 9 cow, 4 sheep | 11 cow, 1 sheep |

Our livestock, fertilizer and melon lines match theirs almost exactly. **The
entire gap is the crop economy**, and we had the land and the labour idle to
grow it. The demand-forecast commit closed part of this (strawberry 52 -> 160,
watering 294 -> 583, idle 3,058 -> 1,359); wheat is still untouched at 28.

Their bank curve is worth memorising: $1-$500 through day 8, $2k day 10, $6.6k
day 12, $19.9k day 16, $44.7k day 20, $82k day 24, $110k day 28. **They are as
broke as we are through the first third.** An idle opening is not the mistake it
looks like.

### Live submissions

Read 2026-08-14. Active pair is **v19 (55503782)** and **v18 (55465607)**; v17
aged out. Frozen copies: v18 = `agents/baseline_k.py`, v19 = `agents/baseline_l.py`.

| | games | record | rating | worst bank | median bank |
| --- | --- | --- | --- | --- | --- |
| v19 | 31 | 16-15 (0.52) | 717 | **$42,524** | $70,354 |
| v18 | 56 | 30-26 (0.54) | 704 | $19,963 | $70,794 |

**The left tail has halved.** v19's worst game banks $42.5k where v18's banks
$20k, against the same median. That was the largest structural problem on the
ladder and the proportional reserve plus the commitment-priced assignment
between them appear to have fixed most of it.

**The margins did convert; the win rate is a different problem.** Split the
ladder games by result:

| | winning margin (mean) | losing margin (mean) | decided by < $10k |
| --- | --- | --- | --- |
| v19 | **+$22,618** | **-$16,289** | 39% |
| v18 | +$16,411 | -$20,545 | 39% |

v19 wins bigger *and* loses smaller than v18 on real opponents, so the local
gains are showing up. What has not moved is the win/loss split, because **39% of
ladder games are decided by under $10,000**. A general margin improvement
spreads itself across every game instead of converting the marginal ones, and
the record is decided by that pile of coin-flips.

So the lever for rating is no longer "bank more" -- it is **win the close games**.
Endgame precision is where a few thousand dollars changes a result: stranded
livestock, an unfilled pen, a weed left standing, a last-day sale mistimed. Each
is worth little on average and could be worth a game in the 39%.

v19 also has only 31 games to v18's 56, and ratings converge slowly, so some of
the gap is simply youth.

**Also read the win rates.** Locally v19 beats v15 by $10,184 and v18 by $6,922
over the season, at 0.70-0.82 paired score. On the ladder it plays 0.52 against a
field averaging 737, barely apart from v18's 0.54. Large local margins are
converting into very little win rate against real opponents -- and win rate is
what the rating is made of. That gap is now the central open question, and it is
the same shape as the very first one this project hit: the local pool, even a
ladder-proven one, is not the field.

## An empty pasture is an option, not waste

Reported from a replay: a pasture built on day 2 still had no animal on it, with
the bank empty. True, and more common than it looks -- **roughly half of every
pen we build is still empty at the final whistle** (47 built across three seeds,
23 never filled, median 11 turns before an animal arrives).

It is not waste. Requiring the bank to hold the animal's price before committing
an action to its pen (`build_ahead_cover` 1.5) is the single worst change
measured on this axis:

| | pens built | never filled | held-out margin |
| --- | --- | --- | --- |
| as shipped | 47 | 23 (49%) | **+$7,972** |
| `build_ahead_cover` 1.5 | **13** | 10 (77%) | **-$34,382** |
| `max_structures_ahead` 2 | 60 | 32 (53%) | +$6,347 |
| `max_structures_ahead` 6 / 8 | | | +$7,421 / +$7,560 |

The cushion builds a third as many pens and the herd never forms. A pen standing
empty is the *option* to buy an animal the turn cash arrives; without one ready,
the purchase waits for a build first and the compounding window closes. Livestock
is the dominant income, so that option is worth far more than the tile.

`max_structures_ahead` 4 is already the optimum in both directions.

One real defect was found and fixed here anyway: `budget` was decremented by
animals bought but not by pens queued ahead, so the same dollars backed a cow pen
and a sheep pen in one pass. It measures *identical* -- the second animal type
reaches that line on almost no call -- and is kept because it is correct, not
because it earned anything.

## Pricing the commitment, not the turn

`greedy` scores a pair `value - dist * action_cost`: a toll for walking, then a
comparison of totals. That prices *one turn* of a decision that commits a unit
for `dist + 1` of them. A $400 job four tiles away and a $340 job next door
score alike, though the second frees the unit four turns sooner to earn again.

`rate` divides by the commitment -- net value per turn occupied -- and it is the
best strategy found so far, but only away from the opening:

| plan | held-out score | margin |
| --- | --- | --- |
| `rrrr` rate throughout | 0.000 | **-$40,732** |
| `gggg` greedy throughout | 0.556 | +$1,081 |
| `ggnn` | 0.703 | +$4,996 |
| **`ggrr`** | **0.824** | **+$6,031** |
| `grrr` | 0.785 | +$7,608 |

With the whole farm inside a few tiles the denominator barely varies, so
dividing by it only amplifies noise -- which is why `rrrr` is catastrophic and
`ggrr` is the best thing measured. `grrr` banks more; `ggrr` ships because the
ladder's rating is computed from win and loss, not from margin.

## The assignment strategy should change as the farm grows

Four strategies live behind `assignment_plan`, one letter per quadrant owned
(`ASSIGNMENT_CODES`), each a re-ordering of the same candidate pairs so the seed
and shed budgets stay in one place:

| code | strategy |
| --- | --- |
| `g` | greedy -- best net value, value and distance traded off |
| `n` | nearest -- closest work first, whatever it pays |
| `j` | jobfirst -- most valuable *job* first, nearest free unit |
| `o` | optimal -- maximise the turn's total assigned value |

Held out against both benchmarks, run statically (mean margin):

| plan | margin | |
| --- | --- | --- |
| `gggg` greedy | +$1,081 | |
| `nnnn` nearest | -$5,873 | |
| `oooo` optimal | -$22,667 | |
| `jjjj` jobfirst | -$33,822 | worst |

`jobfirst` losing hardest kills the theory that greedy wins by giving valuable
jobs the best unit -- the *trade-off* is what earns, not the ranking.

**Switching by quadrant count beats any of them.** `ggnn` -- greedy while the
farm is one or two quadrants, nearest once it spans three or four -- measures
**+$4,408 against v15 and +$4,722 against v18** over 80 games a side, against
+$2,161/+$0 for greedy throughout. A dense farm rewards choosing the best job; a
sprawling one rewards not walking, and movement is 55% of every unit-turn.

`gnnn` scores a higher mean (+$7,395) but almost all of it is v18 (+$14,640 to
v15's +$149). With two benchmarks standing for two economies, beating both is
worth more than beating one twice -- which is the reason for having two.

## Optimal assignment is worse than greedy, and that is the finding

`assign_units` matches units to jobs greedily: best pair, then next best. The
obvious upgrade is to solve the assignment jointly, since greedy demonstrably
mis-handles two units contending for one job. It is implemented -- `_hungarian`
plus `_optimal_pairs`, `assignment: "optimal"` -- and it works exactly as
advertised:

* verified against brute force on 400 random instances: **never** below the true
  maximum-weight matching, strictly better than greedy on 19% of them;
* in real games it beats greedy's assigned value on 28% of turns, is identical
  on the rest, is **never worse**, and adds $12,421 of assigned job value a game;
* it costs 0.23 ms a turn against a 1,000 ms budget.

And the agent gets **$25,078 worse** held out, bank $71,222 -> $58,556.

Checked and ruled out: matching quality (brute-forced), the column cap (median
25 jobs a turn, cap never binds), turn-to-turn churn (U-turns 83 vs 75, work per
move 0.451 vs 0.454), units placed (9.30 vs 9.36) and travel distance (1.90 vs
1.89). Making the matching budget-aware, so no unit is matched to a job the seed
or shed stock cannot supply, changed nothing (-$25,078 against -$25,665).

So the objective is what is wrong, not the solver. `value - distance *
action_cost` prices a *single turn*, but an assignment persists: a unit sent
three tiles away is committed for three turns. Greedy's ordering has an emergent
property the sum does not -- the most valuable job always gets the best-placed
unit, so the most valuable work finishes *soonest*. Maximising the turn's total
trades that sequencing away for jobs that happen to sum higher today.

**Greedy here is not an approximation to optimal; it is a different and better
heuristic.** Ships off. Do not "fix" it again without first replacing the
per-turn score with one that prices the whole commitment.

## The two standing benchmarks: v15 and v18

**Every future candidate is measured against these two before anything else.**
They are the only opponents whose strength is confirmed by the *ladder* rather
than by us, and they are deliberately two different economies rather than two
tunings of one:

| | file | peak live rating | economy |
| --- | --- | --- | --- |
| **v15** | `agents/baseline_j.py` | 753.5 | melon capital pump, livestock-led |
| **v18** | `agents/baseline_k.py` | 786.5 | evolved shop-led, wheat opening |

They are `lab.pool.BENCHMARKS`, they head `POOL`, and they are both in
`SEARCH_POOL` so parameter search optimises against them directly. Beating both
means beating two distinct ways of playing, not one lineage with a knob moved.

Adding them un-saturated the gauntlet, which is the whole point: MEAN fell from
0.990 to 0.897 and WORST from 0.938 to 0.500, because for the first time the
pool contains opponents that are actually our equals. Keep them frozen. Add a
third only when a new agent holds a **higher live rating** than either -- not
because it looks better locally.

## Layer 0: measure phases, not games (`lab/phases.py`)

One number per game cannot distinguish a change that does nothing from one that
gains $8k early and loses $10k late -- which is the shape of most real strategy
changes. `lab/phases.py` reports the margin each phase earned on its own, with
the farm state at each boundary.

Its first run re-read a result that had looked uniformly bad. The wheat opening
**wins** days 0-10 by $447, then loses $16,282 across days 10-20 and $16,046
after. The state table says why: day 20 finds it holding **6 animals against the
melon economy's 14**, three quadrants against four. Wheat earns early but
trickles, and a trickle cannot buy a herd inside the window where livestock
still compounds. That is a fixable problem and a different one from "the wheat
opening is bad".

Use this before concluding anything about a strategy change.

## Layer 1: the first parameter that is a function, not a number

`work_reserve` and `animal_reserve` held back a flat $950. That is two different
policies depending on how income arrives, and nobody noticed because only one
kind of income had ever been tested. After a melon harvest drops $5.6k in a day,
holding $950 costs nothing. In an economy earning $300 a day it means the farm
can never assemble a cow plus its reserve at one moment, so it buys none.

Measured on the wheat opening, day 20 held **6 animals against the opponent's
14**; the same farm reserving proportionally holds **12**, and stranded
livestock -- 5 to 13 animals stuck in the shed for the whole game -- drops to
zero, because we stop buying stock we cannot place.

`scaled_reserve` caps the flat figure at a share of the bank, so a rich farm is
unchanged:

| | melon economy | wheat economy |
| --- | --- | --- |
| flat 450/500 | **-$697** | -$28,642 |
| flat 100/100 | -$8,011 | **-$4,995** |
| `reserve_frac` 0.25 | -$3,913 | **-$4,011** |

The wheat opening goes from -$28,509 to -$4,011, and by phase from
-$32,353 cumulative to -$8,000, now *winning* days 20-30 by $2,414.

This is the shape every remaining parameter should be checked for: a constant
that was fitted under one regime and silently encodes it.

## Layer 3: joint parameter search (`lab/evolve.py`)

`optimize.py` moves one parameter at a time, which is the wrong shape: nearly
every real finding this season has been an *interaction*. `evolve.py` is a
(1+lambda) search that perturbs a random **subset** together, so a pair can move
jointly even when neither helps alone. Three guards: the incumbent is re-scored
on the same seeds as its challengers each generation, every accepted step is
validated on disjoint seeds and both numbers logged, and the objective is a pool
rather than one mirror.

Run from the shop-led defaults it found, in nine generations, a set that turns
**-$4,011 into +$2,161** held out against `baseline_j` -- the first time the
shop-led economy has beaten the melon one. Held-out margin rose with search
margin the whole way, which is what says it is finding signal and not seeds.

The biggest movers were parameters nobody had thought to question: `job_weight`
2.2 -> 1.16, `plant_commitment_cost` 8 -> 20.9, `build_fraction` 0.8 -> 0.2,
`rival_supply_weight` 0.10 -> 0.31, `max_hands` 14 -> 11.

**Watch the checkpoint while it runs.** It rewrites `evolved.json` on every
improvement, so reading the file and applying it are not atomic -- a set was
applied here that differed from the one validated a minute earlier. Stop the
search before adopting, then re-validate exactly what landed in `DEFAULTS`.

## Layer 2 first cut: pricing a tile against the day it sells

`crop_profit` credits a crop the *whole* season's town demand and charges it the
*whole* in-flight supply, whatever day it actually sells. `sale_horizon` scales
both by the fraction of the remaining season that elapses before harvest.

More principled, and it does not pay: -$4,210 naive, -$1,815 once the demand
weights are re-fitted to compensate, against -$697 for leaving it alone. The
weights and the horizon are strongly complementary -- `town_pull_weight` 1.5
alone is -$12,720, and only stops being terrible when the horizon scales it back
down -- so neither can be tuned without the other.

The approximation is what is wrong: supply does **not** arrive evenly, it lands
in lumps on specific harvest days, and every planted tile already carries the
date it will land. A real projection walks the tiles and accumulates per day.
That is the version worth building; the linear share was the cheap sketch.

**A caution this produced.** The phase table for horizon-plus-refitted-weights
showed +$2,823 in the endgame, and it was tempting to read that as "horizon
pricing helps late". It does not -- gated to day 20+ it plays an identical game,
because by then `days_left` is small enough that the share is already 1.0. The
endgame swing came from the weights bundled into the same variant. Change one
thing per phase table.

## Settled, so nobody re-litigates them

- **The melon opening is correct.** It looks wrong in a replay -- 23 melon
  tiles, $148 in the bank on day 9, then the price crashing from $250 to $100 as
  we sell -- and two independent instruments say to leave it alone. Capping
  melon tiles costs $17-30k a game (26 tiles: 0.562 held out; 16: 0.188; 10:
  0.100; 6: 0.006). Reserving tiles for a two-day cash crop costs $7.4k at three
  tiles and $15.6k at six. And the marginal arithmetic agrees: a melon tile is
  worth 14.8 falling to 2.9 as its own supply lands, crossing carrot's 3.7 only
  at the 22nd tile. The top two ladder agents are also broke until day 10.
- **Melon is not worth pacing.** No shop demands it, so the town drains exactly
  30 units a season, 1 a day. Holding melon back cannot let the price recover.
- **Crops are not underpriced for labour.** `job_weight` 1.4/0.8/0.4 and
  `plant_commitment_cost` 20 all measure neutral-to-negative even with half our
  unit-turns idle, and `seed_buffer` 25 costs $6.3k. The crop shortfall was a
  *demand forecasting* failure, not a labour-pricing one.

## Open leads

- **Wheat.** The top agents sell 433 a game; we sell 28, and the market still
  ends 1,158 units below equilibrium with the price high. The demand forecast
  moved strawberry but not wheat. This is the largest single line item left.
- **The left tail — now the biggest open problem.** Ladder banks run $10k-$121k
  where the same agent banks a tight $55-60k locally against a mirror. v15's
  first three games already contain a $10,784 game; v14's recent losses bank
  $36-52k against opponents banking $62-93k. Roughly a third of real games go
  badly wrong in a way no local game does.
  The hypothesis worth testing first: **we commit the whole farm on day 0-2, and
  the shops are not drawn until day 3+.** Our forecast uses the pool average,
  which is right on average and wrong every specific season — a season drawing
  four yarn stores and no bakery leaves the strawberry we planted on the prior
  nearly worthless (measured spread: wool 30-534, carrot 84-570). Look for
  whether the bad games correlate with an unlucky draw against what we planted,
  and if so hold planting capacity back to respond to the actual draw rather
  than spending it all on the prior.
- **Stranded livestock, ~$5k a game, on half of all seeds.** `lab/checks/
  validate.py` reports 4 cows + 7 sheep and 4 cows + 6 sheep sitting unplaced in
  the shed on seeds 1 and 2, while games elsewhere finish with a dozen *empty*
  pastures. Capital that was bought, never placed, and never earned. The old
  note below says stranding was accidentally protecting us from crashing wool --
  that was measured before the demand forecast existed and should be re-tested.
- **The pool needs a real opponent.** Everything in it is our own lineage, and
  we beat all of it. Reconstruct an archetype from a 3,200-rated replay --
  strawberry+wheat at scale over 13 animals -- or the next tuning round fits
  ourselves again.
- **Herd size.** Ladder games we lost had the opponent accumulating more
  animal-days (452, 338, 330); games we won, fewer (0, 0, 112). Locally a bigger
  herd loses. Note the top agents run **13 animals**, close to ours, so the
  ladder correlation is probably a symptom of a stronger economy, not a cause.
- Placing every owned animal is **not** automatically right — stranded stock was
  accidentally protecting us from crashing wool. Fix the buying decision rather
  than forcing placement.
- We build ~12 pastures we never fill; the top agents finish with 0-1 empty.
- Weeds are largely ignored, as they are by strong ladder opponents.

## Verification before any submission

```bash
~/.venvs/kaggri/bin/python -m unittest discover -s tests
~/.venvs/kaggri/bin/python -m ruff check .
~/.venvs/kaggri/bin/python lab/pool.py 24          # gauntlet
```

Then confirm: zero validator issues (`kaggriculture_harness.actions.inspect_action`
over full games), every game `DONE`, p95 turn latency far below the 1s limit
(currently ~0.6ms), and no unsold shed at the final step. Get explicit approval.

## Environment

- Research venv (Linux, fast): `~/.venvs/kaggri` — Python 3.12.13,
  `kaggle-environments==1.32.3`, `kaggle==2.2.4`. Engine verified byte-identical
  to the Windows `.venv` copy.
- The Windows `.venv/` in the repo is retained for parity checks.
- `nproc` reports 32 but parallel throughput saturates near 16 workers.
