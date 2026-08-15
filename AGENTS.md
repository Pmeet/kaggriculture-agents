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

## Audit: which gates decide on one factor

A sweep of every parameter used as a threshold, looking for decisions taken on a
single number. Seven were **pure calendar** -- the day, and nothing else.
Measured, most turned out to be doing very little, and one was hiding a bug.

| gate | relaxing it | verdict |
| --- | --- | --- |
| `hire_hours` (0-3) | **-$23,837** | load-bearing, and for a bad reason |
| `animal_last_day` 20 -> 26 | -$298, -0.019 | mild but real; keep |
| `land_last_day` 19 -> 26 | -$577, 0.913 either way | now redundant, the capacity gate supersedes it |
| `cull_last_day`, `fertilize_last_day` | | inert, features are off |

### Which gates actually fire

Counting how often each threshold is the one blocking, over three full games,
turns out to be the more useful question than whether a gate is multi-factor. A
gate that never fires is a decision that is not being made; a gate that fires
most of the time is doing the steering.

| gate | fires | verdict |
| --- | --- | --- |
| `max_hands` 11 | **72%** | genuinely optimal: 9 costs $9.4k, 14 costs $5.1k, 18 costs $9.0k |
| land affordability | 61% | |
| `land_capacity_slack` 1.35 | 55% | the new gate, and it earns its place |
| `land_last_day` 19 | 33% | redundant now, capacity supersedes it |
| `animal_last_day` 20 | 30% | mild but real, keep |
| `expand_when_empty` 10 | 26% | inert from 5 to 16, then **-$80,733 at 24** |
| `melon_max_tiles` 21 | 16% | barely binds; 24 is identical |
| `carry_limit` 8 | 7% | load-bearing, 14 costs $7.4k |
| `wheat_buy_max_price` 60 | **0%** | dead parameter, see below |

Two results worth keeping. `max_hands` is *not* made redundant by pricing hands
-- with the price test alone the workforce runs to about 18 (18 and 26 measure
identically) and that costs $9k, so the cap adds discipline the price cannot.
And `expand_when_empty` is a guard rail rather than a tuning knob: flat across
its whole useful range, catastrophic past it.

### Feed is never the problem

`wheat_buy_max_price` blocked **0 of 491** turns on which feed was wanted: wheat
trades at $32-36 against a $60 cap. And of the animal-turns spent one missed
feed from death, **none** had an empty shed -- every single one had wheat on
hand. Losing about an animal a game is a *logistics* failure, a hand not
reaching the tile, and no amount of feed budget addresses it.

### The hiring window was hiding a divisor

`needed = ceil(workload * move_factor / hours_left) - have`. As the day runs
out, that divisor shrinks and the shortfall explodes, so hiring in the evening
buys hands at the full `fib(n)` price for two hours of work. `hire_hours` was
not a policy, it was a guard around a formula that misbehaves after noon.

Fixing the cause and pricing the hand instead -- three factors rather than a
clock: the day's workload with the divisor floored, the fib price of the next
hand, and the jobs it can still reach before nightfall -- beats the window on
**both** measures over 96 games a side: **0.948 and +$18,096**, from 0.927 and
+$17,997, and more evenly across the two benchmarks.

Two failed attempts are worth keeping. Removing the window alone costs $23,837.
Replacing the workload term with a pure value test costs $15,000 -- that swapped
a two-factor rule for a one-factor one, which is the opposite of the point. The
gain only appears when workload *and* price are both in the rule.

## Buy a quadrant only if the hands can work it

Reported from a replay: on day 24 the farm held a cow and eight sheep it had
never placed, weeds everywhere, and had still opened a fourth quadrant. The
diagnosis was right -- the land gate asked only "is the farm full and can we
afford it", never "can we work another one".

`land_policy` adds composable tests (`land_is_worth_working`): `c` capacity,
`s` stocked, `d` demand. **The threshold is the entire finding**, and getting it
wrong looks exactly like the idea being wrong:

| capacity slack | held-out score | margin |
| --- | --- | --- |
| off (cash only) | 0.831 | +$12,074 |
| 1.00 -- blocks constantly | 0.594 | +$2,819 |
| **1.35** | **0.913** | **+$17,686** |
| 1.50 | 0.869 | +$17,701 |
| 1.65 -- never binds | 0.831 | +$13,608 |

So: refuse a quadrant while the farm already owes half again more work than its
hands can reach. Worth +$5,612 and +0.08 win rate over buying on cash alone.

The phase table shows what it buys. Days 10-20 turn **positive for the first
time**, +$3,371 against -$1,925 before, and at day 20 the farm now holds **three
quadrants where the opponent holds four** -- and finishes the season with **zero
weeds against their eight**. Staying smaller means the work actually gets done.

The `s` test (no animal waiting, few empty pens) is also positive at a loose
setting -- 8 pens, +$13,650 -- but adds nothing on top of `c`. The `d` test
(unclaimed town demand) never binds below 600 units and is harmful above it.

### Animals in the shed do not run away

Checked in the engine for this: shed contents persist, and our shed never
approaches its cap. But `_drop_inventories_to_shed` deletes whatever a hand is
still *carrying* at nightfall when the shed has no room -- `del inv[item]` runs
whether or not the drop fit. We lose about **one animal a game**, and it is
starvation of a placed animal (two missed feeds), not the shed.

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

## Yes, local games have shops -- and the seeds cover the spread

Worth confirming because so much of the strategy hangs on the shop draw. Every
local game runs the full town: `env.info["seed"]` is populated from
`configuration={"seed": N}`, so the draw varies properly.

Across seeds 1-24 and 1001-1024, **every seed produced a distinct shop line-up**,
and the extremes are represented -- up to **four copies of one shop** in a single
game, which is the case that makes a season lopsided.

| product | min | median | max | seeds with **zero** demand |
| --- | --- | --- | --- | --- |
| wheat | 2 | 5 | 7 | 0 |
| strawberry | 1 | 4 | 7 | 0 |
| milk | 0 | 3 | 6 | 1-2 of 24 |
| carrot | 0 | 3 | 9 | 2-3 of 24 |
| **wool** | 0 | 2 | 6 | **7-9 of 24** |

So roughly a third of games contain no yarn store at all, and wheat and
strawberry are never absent -- which is the empirical version of their 5/8 and
4/8 share of the shop pool.

**A subtlety when reasoning about seeds.** The shop line-up is *not* a pure
function of the seed. `_end_of_day` seeds one RNG per day and `_spawn_weeds`
draws from it for every empty tile *before* the shop choice is made, so the draw
depends on how the agents played. Both seats of a paired game still see the same
town, so common random numbers still hold within a pair -- but do not expect to
reproduce a line-up offline, and do not assume two different candidates saw the
same shops on the same seed.

### Sheep are not adapted to wool demand, and it does not matter

The obvious worry: in the third of games with no yarn store, are we still buying
sheep? Yes -- 5.6 bought against 6.1 when wool is wanted, so the agent is not
adapting at all. It costs nothing: those games bank **$82,900 against $77,798**,
and wool sold is 49 against 43. The town centre drains ~29 wool a season whatever
the shops do, and we sell roughly what gets absorbed either way.

What the same measurement did turn up: **~6 sheep bought, ~2.5 on the board at
the end.** That gap, not the demand mismatch, is where the sheep money goes.

## One branch per agent version

Each candidate is developed on its own branch, cut fresh from `main`:

```bash
git checkout main && git pull
git checkout -b agent/v23
```

Work happens in `main.py`. When the candidate is frozen for submission, copy it
to the next `agents/baseline_*.py`, record its submission id and label in
`lab/submissions.json`, and merge the branch back into `main`.

**Merging back is not bookkeeping.** Frozen snapshots are the only opponents we
have, so a version that never reaches `main` is one the next candidate can never
be measured against.

### The branch can still fight every earlier agent

Opponents resolve as Python modules from the working tree, not from git history,
and every frozen snapshot lives in `agents/`. A branch cut from `main` therefore
carries all of them, and `agent/v23` scores against the recent submissions
without switching branches or checking anything out:

```bash
python lab/ab.py --seeds 40 --variant 'cand:{}'
```

`--opponent` defaults to `recent`: the last six labels in
`lab/submissions.json`, resolved by `lab/versions.py` on every run. Pass
`recent:7` for a wider set, or a label (`v21`) or inclusive range (`v18..v21`)
for something narrower.

**Never write version numbers into a script or a checklist.** A hardcoded
opponent set is right on the day it is written and quietly wrong one submission
later, when it is still grading candidates against agents we have already
beaten -- trap 5 from *Where things stand*, wearing a different hat. `recent`
raises its own bar; `v18..v21` does not.

### `agents/` is append-only

Adding a snapshot is the only permitted change to `agents/`. Editing one
retroactively changes what every past measurement meant, and nothing complains:
the module still imports, the gauntlet still prints a number, and that number
still looks like yesterday's.

```bash
python lab/checks/frozen.py
```

checks that every snapshot on the branch is byte-identical to `main`, and that
every opponent named in `benchmarks.json` and `submissions.json` imports and
exposes an agent. It exits non-zero, so it can gate CI or a pre-push hook.

## Pre-ship checklist

Run these in order. The first step is the one that keeps every later number
honest, and it is the one that was being skipped.

1. **Refresh the benchmarks from the ladder.**
   `python lab/benchmarks.py --refresh`
   It ranks our own submissions by live rating, drops any with fewer than 25
   games so a fresh 600-seed cannot displace a proven agent, keeps only those
   with a frozen snapshot, and writes `lab/benchmarks.json`, which `lab/pool.py`
   reads. Hand-picking a benchmark pair goes stale the moment a newer agent
   climbs past it, and then every measurement is taken against something we have
   already beaten.
2. **Score the candidate against them**, at 40 seeds or more.
   `python lab/ab.py --seeds 40 --opponent benchmarks --variant 'cand:{}'`
   Then against the recent field, which is the harder bar and the default:
   `python lab/ab.py --seeds 40 --variant 'cand:{}'`
3. **Confirm no frozen agent drifted.** `python lab/checks/frozen.py`
   A modified snapshot makes every number above incomparable to every number
   recorded before it, silently.
4. `python -m unittest discover -s tests` and `python -m ruff check .`
5. `python lab/checks/validate.py` -- zero issues, every game DONE, nothing
   unsold in the shed.
6. `python lab/pool.py 20` as a regression check, not a steering signal.
7. `python lab/phases.py` if the change is meant to affect a particular phase.

**Forty seeds is the floor.** The same candidate measured over 5 seeds scored
0.900 on one seed set and 0.750 on the other -- a 0.15 swing between two 20-game
samples. Twenty games decides nothing here.

### What the ranking costs

Ranking benchmarks by rating buys currency and loses variety: v21 and v20 are
both shop-led descendants of one another, where the old hand-picked pair
deliberately held one melon economy and one shop-led. `MELON_FOIL`
(`agents/baseline_j.py`) therefore stays in the wider `POOL` permanently even
when its rating drops it out of the benchmark pair -- it is the only opponent
left that plays a genuinely different game.

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

## The plan and the weights have to be fitted together

The second joint search settles a question the first could not ask. `evolve.py`
now mutates `assignment_plan` as a categorical alongside the numbers, and the
answer it reaches is `grrn` -- the plan rejected a day earlier in favour of
`ggrr`, on the correct reasoning that `ggrr` won on win rate under the *then*
parameters.

Under the new weights that reverses, and not marginally:

| | held-out score | margin |
| --- | --- | --- |
| previous defaults (`ggrr`) | 0.744 | +$7,972 |
| **evolved (`grrn`)** | **0.831** | **+$12,074** |
| evolved, plan forced back to `ggrr` | 0.694 | +$7,786 |

Forcing the old plan onto the new weights costs more than the weights gained.
The plan and the weights are one decision, and any future sweep of either alone
is measuring a coupling it cannot see.

`town_pull_weight` fell to 0.1, its lower bound, which is worth re-running with a
wider floor before trusting it.

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

## The per-day ledger: built, measured, and off (2026-08-15)

The refinement the horizon note below asks for -- "supply does not arrive
evenly, it lands in lumps on specific harvest days, and every planted tile
already carries the date it will land. A real projection walks the tiles and
accumulates per day. That is the version worth building" -- has now been built.
It is behind `ledger_pricing` and it is **off**, because it loses.

`market_ledger` walks both farms and accumulates each committed block of
production on its landing day against the town's per-day drain;
`ledger_crop_revenue` prices each yield of a candidate planting at the
projected inventory on the day it lands, and `animal_profit` does the same per
production tick. Full write-up in `APPROACH.md`.

| variant, 40 seeds a side vs both benchmarks | search | holdout | margin |
| --- | --- | --- | --- |
| **control (shipped)** | **0.875** | **0.825** | **+$8,738** |
| ledger, crops only | 0.494 | 0.381 | -$3,781 |
| ledger, crops + animals | 0.463 | 0.362 | -$3,492 |

Three results worth keeping, whatever happens to the ledger itself.

**Dated pricing is blind to the replant, and that is most of the naive loss.**
A wheat tile frees on day 4 and goes again. Pricing one cycle books only the
first harvest, which unpriced the short-crop opening outright: the first naive
run scored **0.000, -$40,732**. `ledger_chain` prices the tile as the chain of
plantings it enables, later cycles net of their own labour, and that restores
the opening -- day-0 wheat job value -24 to +30, and a trace with 19 wheat
tiles by day 2 and a wheat line all season, which is the leaders' shape. It is
worth ~$30k over naive and still short of control.

**The drain weight is a peak, not a slope, and the obvious analogy is wrong.**
`town_pull_weight` settled at 0.1, so the natural guess was that the ledger
should also believe about a tenth of the projected drain. Measured over 16
seeds, that guess is catastrophic and backwards:

| `ledger_drain_weight` | holdout | margin |
| --- | --- | --- |
| 0.10 | 0.062 | -$23,370 |
| 0.25 | 0.078 | -$19,918 |
| **0.50** | **0.500** | **+$324** |
| 1.00 | (0.362 at 40 seeds) | -$3,492 |
| 1.50 | 0.000 | -$38,931 |

The two weights are not the same quantity. `town_pull` is subtracted from a
season total; the ledger's drain accumulates day by day and sets the *level*
the price curve is read at, so starving it collapses projected inventory and
the below-base branch of `price_at` then inflates everything.

**Never edit `main.py` while a harness run is in flight.** `lab/arena.run_match`
builds a fresh `ProcessPoolExecutor` per call, so workers spawned after an edit
import the new file: arms of the same table end up measured against different
code. One 40-seed run was discarded and re-run for this. Nothing warns you --
the numbers still print.

And the standing trap, hit again: the crops+animals variant measured **+$2,770
held out over 8 seeds** and **-$3,492 over 40**. Forty seeds is the floor.

### Fixed on the way, worth porting

`animal_profit` priced fertilizer and feed at a flat season price. Fertilizer
falls from about $100 to $30 across a season while wheat climbs, so the flat
figure overstates the dung and understates the feed. The dated version is
currently reachable only in ledger mode; it is a change worth measuring on the
shipped model in its own right.

### The joint re-fit was run, and the ledger still loses

The re-fitting hypothesis was the right one and it was not enough. Five
generations of `lab/evolve.py --start` from a ledger agent, then all three arms
measured at 40 seeds against the benchmarks:

| arm | search | holdout | margin |
| --- | --- | --- | --- |
| **control (shipped)** | **0.875** | **0.825** | **+$8,738** |
| evolved params, ledger **off** | 0.044 | 0.037 | -$21,467 |
| evolved params, ledger **on** | 0.619 | 0.594 | +$5,609 |

Read the middle row first: the evolved parameters are **catastrophic without
the ledger**. They were fitted to its value scale, so the set is not a general
improvement that happens to include a ledger -- it is a set that only makes
sense with one. The ledger is worth **+$27,076** to its own co-fitted
parameters, which is the cleanest evidence that the model does real work.

And it still does not clear the shipped agent: 0.594 / +$5,609 against 0.825 /
+$8,738. So **the ledger is not adopted.** It went from -$3,492 to +$5,609
under joint search and remains $3,129 and 0.23 win rate short.

One caveat recorded honestly rather than acted on: `evolve` searched against
its default pool (`baseline_j`, `baseline_b`), where it reached +$14,600 held
out, and only +$5,609 of that transferred to the benchmarks. That is opponent
overfitting, and the fix is *not* to re-run the search against the benchmarks
themselves -- that would fit the thing we validate on. It is the same warning
the pool-saturation note makes: the local pool is not the field.

Do not restart this from scratch. The mechanism is sound and measured; what it
lacks is a reason to believe another tuning round closes a $3k gap that four
hand-tuned weights and a joint search did not.

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
  `kaggle-environments==1.32.6`, `kaggle==2.2.4`. **This is the post-rebalance
  engine the ladder runs. Measure here, and only here.**
- The Windows `.venv/` in the repo is **stale**: `kaggle-environments==1.32.3`,
  the pre-rebalance engine, untouched since 2026-08-04. It is not a parity
  check and has not been one since the ladder moved. Do not run measurements
  against it.
- `nproc` reports 32 but parallel throughput saturates near 16 workers.

The two engines differ in shop unlocking (drawn with replacement and capped at
`MAX_SHOP_INSTANCES` = 8, against the old draw without replacement), town centre
demand (`townCenterSellInterval` 24 flat, against 12 with a rising multiplier),
`shedCapacity` enforcement on purchases, and PLACE/LOCKED ordering. Crops,
animals and the price curve did **not** change, so the plant and animal
lifecycles and the whole market model still read the same in both.

**Verify the engine from a live replay before trusting any tuning.** The
decisive check is a replay of one of our own submissions: `configuration`
records `townCenterSellInterval` (24 = rebalanced, 12 = old), and
`unlocked_shops` contains duplicates only post-rebalance. The move was never
announced in the repo, and days of parameter tuning were once measured against
the wrong game before anyone noticed. Re-check after any gap in work, or
whenever results stop making sense.
