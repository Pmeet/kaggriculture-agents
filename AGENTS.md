# Kaggriculture Agent Handoff

Last updated: 2026-08-19 (Asia/Calcutta)

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

Read **2026-08-19** from the live API. **Rank 2529 of 5202; rating 769.2**
against a field median of 741.5 and a leader at 3182.0. Local gauntlet ~1.0,
ladder ~0.46. Trust the ladder.

Percentile has not moved in eight days: 1929/3809 on 08-11 was the 51st
percentile, 2529/5202 today is the 49th. The rating rose 717.7 -> 769.2 and
bought nothing, because the whole field rose with it.

**The distribution is what matters, and it is bimodal.** Median 741.5, but p75
is 1648.1 and p90 is 2225.4. Half the board is parked near 740 (single or
abandoned submissions); the real competition starts around 1600. We are at the
top of the parked half, not the bottom of the serious one.

| target | rating needed | ours |
| --- | --- | --- |
| top 5 (the goal) | ~2,920 | 769.2 |
| top 100 | 2,677.2 | |
| top 500 | 2,240.6 | |

Closing that is not a tuning problem. Nothing in the parameter-search layers
moves a rating by 4x.

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

Read 2026-08-19. Active pair is **v21 (55512749)** and **v22 (55521764)**.
Frozen copies: v21 = `agents/baseline_n.py`, v22 = `agents/baseline_o.py`.

| | games | record | rating | median bank | opp mean bank | mean opp rating |
| --- | --- | --- | --- | --- | --- | --- |
| v20 | 38 | 22-16 (0.58) | 788.8 | $66,817 | $69,791 | 746 |
| v21 | 95 | 43-52 (**0.45**) | 769.2 | **$75,088** | **$82,303** | 796 |
| v22 | 85 | 40-45 (0.47) | 763.7 | $71,284 | $80,466 | 778 |
| v18 | 56 | 30-26 (0.54) | 767.7 | $70,100 | $70,027 | 747 |

Read the first two columns together and the agent looks broken: **v21 has the
highest median bank we have ever put on the ladder and the worst record.** It is
not broken. It is playing a different field.

### The field is inflating faster than we are improving

The controlled version, which removes every confound because the agent is frozen
code: split v21's own 95 games by day.

| day | games | mean opp rating | our bank | opp bank | rate |
| --- | --- | --- | --- | --- | --- |
| 08-14 | 35 | 785 | $77,539 | $75,960 | 0.57 |
| 08-15 | 18 | 826 | $69,695 | $92,063 | 0.28 |
| 08-16 | 18 | 776 | $71,853 | $69,816 | 0.67 |
| 08-17 | 16 | 816 | $76,872 | $90,298 | 0.25 |
| 08-18 | 8 | 788 | $68,311 | **$100,197** | 0.25 |

Compare the first and last rows. **Opponents rated 785 banked $75,960 on 08-14;
opponents rated 788 banked $100,197 on 08-18** -- the same rating buys a 32%
stronger economy four days later. Our own bank is flat across the whole table.
v22 shows the same drift over its shorter life ($79,011 -> $85,066 opponent
bank, 0.53 -> 0.29).

Three consequences, and the third is the expensive one:

1. **A rating is only comparable to ratings earned the same week.** v20's 788.8
   was won against a 746 field and has been frozen since 08-15; v22's 763.7 is
   being marked to a 778 field today. Ranking them against each other, which is
   exactly what `lab/benchmarks.py` does, silently prefers the older agent. The
   minimum-games guard does not help -- it makes it worse, by favouring agents
   that have stopped playing.
2. **Standing still loses ground.** Percentile is flat over eight days while the
   rating climbed 50 points. Any week without a shipped improvement is a week of
   decline.
3. **Incremental margin work has stopped paying.** The prior read said the lever
   was "win the close games", because 39% were decided by under $10k and we were
   level with the field on banks. That was true on 08-14 and is not true now: at
   v21's last measured day we are outbanked by **$31,886 on average**, and only
   25% of its games are close. There is no endgame precision worth $32k. The
   lever is back to economy, and it is the crop economy -- see the wheat line in
   *Open leads*, still 28 sold against the top agents' 433.

## The ladder moved to 1.32.7 on 2026-08-15, and it repriced scarcity

Found 2026-08-19 from stickied staff topic 735311, "Small balance change"
(Bovard Doerschuk-Tiberi, 2026-08-15 00:30Z); `kaggle-environments` 1.32.7
published 01:35Z the same night. **The second time this has happened silently.**

Verified rather than inferred: replay 94245846 (v21, played 08-18) disagrees with
1.32.6 on five sampled prices and with 1.32.7 on none. The research venv has been
upgraded; the ladder runs 1.32.7 and so do we.

What changed -- a new `hinge` shape on the **scarcity** side only, for three
products:

| product | before | after | scarce price at the deficit our games reach |
| --- | --- | --- | --- |
| CARROT | `log`, 0.20 | `hinge`, **1.00** | -549: $42 -> **$91** |
| TOMATO | `linear`, 0.40 | `hinge`, 0.40 | -369: $104 -> **$241** |
| EGG | `linear`, 0.40 | `hinge`, 0.40 | -550: $83 -> **$152** |

`hinge` is linear in x/T below the knee and picks up a quadratic term (gain 8)
above it, so price is calm until a product is genuinely scarce and then runs
away. Crops, animals, lifecycles and every glut-side curve are untouched.

**This is almost certainly what the "field inflation" reading was.** Opponent
banks jumped from ~$76k on 08-14 to ~$100k on 08-18 against a fixed v21 -- and
08-15 is when the engine started paying several times more for three products.
Prefer this explanation to "the field got better at farming" until something
distinguishes them.

### What staff said, and what a competitor measured

Topic 735311, in full. Bovard (staff): the change makes egg, tomato and carrot
"increase significantly if there is a large shop demand and no production", with
stated firing rates **assuming no production** of tomato 50%, carrot 26%, egg 22%
of games. Intent: "roughly preserve the existing market dynamics, but make these
products viable in some situations, not universally... more interesting end game
decisions." Implementation is Kaggle/kaggle-environments PR #1399. **"This should
be the last change, excepting game breaking bugs."**

destbreso (754th) independently reproduced it over 120 replayed episodes, and
their numbers change how much we should want this:

- Firing rates land close to stated: tomato 55.0%, carrot 28.3%, egg 25.8%.
  Melon is the control -- untouched, in no shop menu, 0 of 120 crossings.
- **The median game is the old game.** Median scarcity sits just *below* each new
  knee (tomato 219 v 200, carrot 316 v 450, egg 228 v 332), and dumping 100 units
  at median scarcity pays **1.00x** the old revenue for tomato and egg. It is ~2x
  at p90, and the large multiples appear only in the deepest game of 120.
- **Egg never reaches the money**: 1.00x at median and p75, 1.06x at p90.
- Carrot's `below_target` 0.20 -> 1.00 is real and unannounced -- they flagged the
  same omission we found independently.
- Switching build with agent, seed and opponent fixed moved 118 of 224 banks and
  **changed 0 of 224 winners**. Recorded episodes replay identically on either
  build, 40 of 40 to the dollar.

So this is a **dispersion change, not a level change**: nothing at the median, a
long tail in the minority of games with a big shop draw and no producer. Our
"largest untouched line item" framing was too strong -- it is a conditional tail
opportunity in roughly a quarter to a half of games, and egg is likely not worth
chasing at all.

### The objective is Pr[win], not margin -- and that is our open question answered

destbreso's closing point is the most useful thing in the thread. A change that
adds nothing to the median and much to the tail moves **dispersion**, and
"dispersion and expectation point different ways depending on whether you are
ahead or behind". They argue the objective is **Pr[win] = Phi(mu/sigma)** rather
than expected margin.

That is the answer to the question this file has carried for a week: *why do
large local margins convert into almost no win rate?* Because we have been
steering on mu alone while our sigma is enormous -- ladder banks $10k-$121k
against a tight $76-93k locally. Raising mu by $12k does little to Phi(mu/sigma)
when sigma is ~$40k; halving sigma does more. **Cutting the left tail is
mathematically equivalent to a large margin gain, and we have been treating it as
a lesser, separate problem.**

Practical rule: report mu, sigma and Phi(mu/sigma) together, and never accept a
change that raises mu while widening sigma more.

### What we changed, and the trap we walked into

`price_at` in `main.py` now mirrors 1.32.7 exactly (0 mismatches over the whole
curve; `tests/test_agent.py` pins it). It was wrong for four days, which matters
because it decides what we sell.

Planting is deliberately **still valued on the pre-1.32.7 curve**, via
`planting_price`. Letting the new prices drive the crop mix measured
**-$34,044 a game over six seeds**: the agent front-loads carrot, the livestock
build slips behind it, and ten pastures finish empty. Note the first mitigation
tried -- clamping the valuation at the hinge knee -- changed *nothing*, because
the deficits reached in valuation sit below T=450 and the damage comes from
carrot's target going 0.20 -> 1.00, which lifts the whole curve rather than just
the runaway tail. Measure before believing a fix.

## Animals bought, carried, and never delivered -- fixed, +$25k

The walking measurement said the lever was routing. It was not, and the way that
came apart is worth keeping.

**Pricing the walk higher is strictly worse.** Sweeping the parameters that exist
for exactly this, over 16 seeds against v21 and v22:

| variant | search score | margin | holdout |
| --- | --- | --- | --- |
| control | 0.641 | +$4,965 | 0.656 |
| `action_cost_scale` 0.75 | 0.078 | -$21,534 | 0.109 |
| `action_cost_scale` 1.0 | 0.016 | -$26,405 | 0.000 |
| `action_cost_floor` 16 | 0.008 | -$28,249 | 0.000 |
| `action_cost_floor` 24 | 0.359 | -$4,402 | 0.375 |

So walking was never mispriced. Splitting the work by tile type found the real
shape: animal tiles carry four jobs a day, so a unit parked on a herd works
without moving. THUNDER THUNDER does **949 animal jobs at 0.39 tiles each**; we
did **386 at 1.53**. Our herd is *tighter* than theirs (spread 1.12 against
2.08) -- it was simply five animals against fourteen. The walking was downstream
of the herd.

**The herd was small because animals were bought and never delivered.** Tracing
every purchase: seed 2 bought 17, placed 9, and finished with ten animals *in
units' hands* against ten empty pens. Two bugs in series:

1. The PLACE job required stock in the **shed**. PICKUP empties the shed, so the
   job vanished on the very next turn and stranded the carrier.
2. Animals are not in `PRODUCTS`, so neither the carry-limit drop nor the
   filler-assignment guard noticed a unit holding one. It wandered off doing
   filler work with a cow in hand, for the rest of the game.

Fixed by counting carried animals when building the job, and by committing a
unit that holds one to the nearest matching pen. Every animal now lands: seed 2
goes from 9 placed to 15, on the board from day 16.

| | before | after |
| --- | --- | --- |
| score vs v21, v22 (24 seeds) | 0.641 | **0.990** search / **1.000** held out |
| margin | +$4,965 | **+$24,544** / **+$28,696** |
| jobs done per game | 1,936 | 2,386 |
| working share of actions | 27.5% | 33.6% |
| walk per job | 2.02 | 1.66 |
| idle share | 16.9% | 10.6% |
| `validate.py` stranded livestock | 4 cows + 7 sheep | **none** |

Dispersion, on the discipline above: mu +$27,721 sigma $14,512 (mu/sigma 1.91,
Phi 0.972) against v21; mu +$21,367 sigma $12,653 (1.69, Phi 0.954) against v22.
Worst local game banks $58,243, where the ladder left tail used to reach $10k.
Phi tracks the observed win rate closely, so the model is calibrated here.

**Read the 0.99 with trap 5 in mind.** The local pool is saturated again; this
says the change is not a regression and that the left tail moved, not that it is
worth 30 rating points. The ladder decides.

Still short of the top agents: 33.6% working against THUNDER's 41.2%, and 1.66
walk per job against 1.02. The remaining gap is now mostly crop-side routing.

## Items 1 and 2 from the tracking report: one was already done, one works split

Worked 2026-08-19 after the top-20 profile put "harvest more" and "fertilise" at
the top of the list. Both answers were different from the prediction.

### Harvest: the count gap is cadence, not lost value

The report read HARVEST 271 against the consensus 399 as a third of our crop
going unpicked. It is not. Measured directly:

- **Animal production lost to the `max_held` cap: zero.** 334 productions over
  three games, none capped, no animal-day spent at capacity. Fewer, larger
  harvests are *cheaper* than theirs, not worse.
- **Crop left in the field: $95**, and $849 in units' hands -- already closed by
  the liquidation change earlier today.

So >95% of producible units are collected and the remaining count difference is
harvest cadence. There is no third of a farm going missing.

**One real defect did turn up while checking, and it still does not pay.** Wheat
peaked at 3 units of a possible 4, never once 4, over 116 tiles: the harvest
branch `continue`d past the watering block, so the last window watering (wheat's
window is ages 2-4 and `harvest_age` is 4) was never offered. Fixing it works --
mean peak 2.6 -> 3.2, 62 of 112 tiles reaching 4 -- and **loses $1,367 held out**.
One extra action per tile buys one unit of the cheapest product on the board, and
that action was already earning more elsewhere. `water_before_harvest` stays off,
switch retained.

### Fertiliser: the old sweep could not test the thing that works

`fertilize_min_edge` was set to 1e9 after a sweep that found "less is always
better", with a good mechanism: an ongoing crop only banks the bonus on a day it
is also watered, so fertilising demands *extra* waterings and crowds out the ones
already earning -- 58 FERTILIZE cost 122 waterings and strawberry sold fell.

That mechanism does not exist for a one-time crop. Wheat's three window waterings
each add 2 instead of 1 **on the same turns**; nothing extra is asked for. The
old sweep could only turn both on together, so it never tested this.

Split into `fertilize_once_edge`, applied to non-ongoing crops only:

| | search | holdout |
| --- | --- | --- |
| off (1e9) | 0.792, +$1,986 | 0.833, +$1,806 |
| edge 0.25 | 0.833, +$2,697 | 0.875, +$2,365 |
| **edge 0.5** | **0.833, +$2,661** | **0.875, +$2,407** |
| edge 1.0 | 0.833, +$2,620 | 0.875, +$2,314 |
| edge 2.0 | 0.833, +$2,535 | 0.875, +$2,427 |

The optimum is flat from 0.25 to 2.0, which is the reassuring shape -- this is
not a value fitted to the seeds. Taken at 0.5.

Note the two are **substitutes, not complements**: with fertiliser on, adding
`water_before_harvest` costs a further $1,248. Both buy the same missing wheat
units, and fertiliser buys them without spending an action per tile.

**The headroom is real, and the obvious way to reach it is ruinous.** We issue 17
FERTILIZE a game against the consensus 70 and tetsuya's 132, already worth ~$140
an action. Instrumenting the job showed the constraint is not price and not the
edge: the job is *offered* 1,471 times but on only **88 turns of 719**, because
**fertilizer stock sits at zero on 326 turns**. We collect ~257 a game and sell
essentially all of it.

So hold some back -- and it collapses. Against v24, held out:

| `fertilizer_reserve` | score | margin |
| --- | --- | --- |
| 0 | 0.875 | +$2,407 |
| 8 | 0.208 | **-$3,951** |
| 16 | 0.000 | **-$29,050** |

Fertilizer is a real revenue line, and the shed is capacity 100: holding it both
forgoes the sale and crowds out produce, which then overflows and is discarded.
Whatever lets the top agents fertilise 70-132 times a game, **it is not
hoarding** -- more likely they collect on a different schedule, or apply it
straight from the animal tile without a shed round trip. Left at 0; the parameter
stays so the result is not rediscovered.

### Candidate standing, 50 seeds a side against the benchmark pair

**0.840 search / 0.870 held out, +$4,249 / +$4,248** (v24 +$2,685, v23 +$5,811),
over 200 games a seed set. Gate clean: 104 tests, ruff, validator zero issues and
no stranded livestock, every game DONE, shed empty, p95 1.00ms.

## Perturbing a job price tests it; reading it only reports a belief

The value table below shows what the agent *believes* each job is worth. To test
whether the belief is right, scale one job's price and watch the bank: a
correctly-priced job loses money when moved either way. Two diagnostic knobs
exist for this, `fertilize_value_scale` and `water_value_scale`, both 1.0.

**FERTILIZE is priced irrelevantly, not wrongly.** Over an eightfold range the
result does not move: held out against v24, x0.5 gives +$2,477, x1 +$2,483, x2
+$2,310, x4 +$2,732 -- all inside noise. Even at four times its price it is still
far below watering, so the ranking never changes. That settles the earlier
question: we fertilise 17 times because the job is genuinely low-value, and no
re-pricing reaches it.

**WATER is where it gets interesting, and it is a dispersion result.** Over 40
held-out games against v24:

| variant | win rate | mu | sigma | mu/sigma | Phi | worst bank |
| --- | --- | --- | --- | --- | --- | --- |
| **baseline** | **0.900** | +$2,483 | **$2,954** | **0.84** | **0.800** | **$53,071** |
| water x0.7 | 0.700 | **+$5,950** | $8,482 | 0.70 | 0.758 | $36,701 |
| water x1.4 | 0.775 | +$3,404 | $6,206 | 0.55 | 0.708 | $51,859 |

Under-pricing watering **more than doubles the average margin** -- +$5,950
against +$2,483 -- and *loses* two hundred points of win rate, because sigma
nearly triples and the worst game drops $16k. Steering on margin alone would
have taken it.

This is the concrete case for the Pr[win] = Phi(mu/sigma) objective, and it is
the first time the two metrics have pointed in opposite directions on this
agent. **Report mu, sigma and the win rate together; never accept a margin gain
without checking sigma.** `lab/ab.py` reports score and margin side by side for
exactly this reason.

Watering is also the agent's variance control: it is the job that prevents total
loss on a tile, so pricing it high trades expected margin for reliability. That
is the right trade when the objective is wins.

## Why FERTILIZE fires 17 times, and why that is close to correct

Chased on Meet's suggestion that free daily fertilizer plus idle units should
mean far more of it. Four engine facts first, because three of them settle parts
of the question outright:

- **There is no per-unit inventory cap.** `_inv_add` just increments. A unit can
  carry any amount, and each unit has its own dict, so items do stack per hand.
- **Nothing survives the night in hand.** `_drop_inventories_to_shed` empties
  every inventory into the shed at day end and **discards the overflow**, then
  `inventories` resets. Stockpiling in hand across days is impossible.
- **Hands do not persist either** -- `farm["hands"] = []` nightly -- so a hand
  hired tomorrow is a new unit with nothing in it.
- **Collection is not the leak.** We collect 256-280 a game against 289-302 ever
  available.

And the idle window is much smaller than it looks. Idle unit-turns where
fertilizer is waiting *and* a fertilisable crop exists: **43-47 a game**, not
hundreds, because `fertilize_gain > 0` needs a one-time crop inside a narrow age
window.

**The real answer is in the job values.** Median value of each job as offered,
one game:

| job | offered | median $ | p90 $ |
| --- | --- | --- | --- |
| WATER | 7,407 | **275** | 803 |
| FEED | 3,936 | 158 | 515 |
| HARVEST | 2,786 | 99 | 1,100 |
| **FERTILIZE** | 1,437 | **84** | 95 |
| CARE | 3,825 | 74 | 173 |
| PLANT | 2,305 | 52 | 661 |

FERTILIZE is offered 1,437 times and is worth a median $84 against watering's
$275, with a p90 of only $95 -- it is never a high-value job. **The greedy is
ranking it correctly.** We fertilise 17 times because that is how often it is the
best thing a unit can do; forcing more displaces watering worth three times as
much. The 17 are already worth ~$140 an action, which is the return on taking
only the good ones.

That also explains tetsuya's 132: they water **853** against the consensus 909.
A farm with fewer waterable tiles lets fertilising win more often. It is a
different farm shape, not a scheduling trick.

### What was tried on this line

| change | held out vs v24 |
| --- | --- |
| baseline | +$2,407 |
| **source fertilizer from the herd, not the shed** | **+$2,534** (kept) |
| `work_in_passing` on | +$1,986 |
| `fertilizer_reserve` 8 | -$3,951 |
| `water_before_harvest` on | +$1,040 |

Only the herd-sourcing helps, and only slightly -- it takes the cheaper of the
shed route and the nearest animal, so it is never worse by construction, and
FERTILIZE count barely moves (17 -> 18). The shed round trip was not the
constraint either.

**Five scheduling heuristics have now been tried on this agent and four lost.**
The greedy with correctly-priced jobs is a stronger baseline than it looks, which
is the main argument against building a per-unit route planner: it would have to
beat a ranking that the evidence says is already right.

## The top 20 is one agent, and the gap is execution not strategy

Pulled 2026-08-19 with `lab/scout.py`, profiled with `lab/profile_top.py`. The
route is not obvious and is worth writing down: `ListEpisodes` needs a submission
id, the leaderboard only gives team ids, and
`SubmissionService/ListTeamPublicSubmissions` bridges them -- but only with a
browser session (cookie + `x-xsrf-token`), not the API token.

**Fifteen of the twenty-two teams profiled are behaviourally identical**, matching
within 2% on every action count: water 909, harvest 399, plant 184, fertilize 70,
12 hands, 14 animals, walk 1.32 tiles a job. That is a shared public notebook, not
fifteen strategies. Only three profiles are meaningfully distinct.

So the pool needs **three opponents, not twenty**:

| | consensus (15 teams) | tetsuya (rank 1) | ReCurSiON (rank 3) | **ours (v25)** |
| --- | --- | --- | --- | --- |
| work % of actions | 39.6 | 39.4 | **42.6** | **30.7** |
| walk per job | 1.32 | 1.05 | **1.02** | **1.87** |
| walk per animal job | 0.77 | 0.43 | **0.35** | **1.48** |
| hands / animals | 12 / 14 | 12 / 15 | 14 / 13 | 12 / 12 |
| WATER | 909 | 853 | 1010 | 852 |
| HARVEST | 399 | 413 | 390 | **271** |
| PLANT | 184 | 198 | 199 | 186 |
| FERTILIZE | 70 | **132** | 72 | **0** |
| FEED / CARE | 321 / 318 | 349 / 349 | 290 / 285 | 269 / 265 |
| DIG | 31 | 33 | 41 | **57** |

**The crop mix is no longer the gap.** We plant essentially their farm: wheat 121
against 125, strawberry 46 against 42, melon 19 against 12, carrot 0 against 5.
The v23-v25 work closed what the 08-11 replay study identified. What is left is
entirely execution:

1. **HARVEST 271 against 399.** We grow the same farm and pick a third less of it.
2. **FERTILIZE 0 against 70**, and tetsuya -- the rank 1 agent -- runs **132**.
   The single clearest thing the best agent does that nobody else does.
3. **walk per job 1.87 against 1.32**, and 1.48 against 0.77 on animal tiles.
4. **DIG 57 against 31.** We spend 26 extra actions clearing weeds, which is a
   symptom: tiles die because they were not harvested in time.

Note what is *not* different: hands, quadrants, water, plant counts are all level.
This is not a strategy deficit any more, it is throughput.

### What to build, given the monoculture

Three opponents, in order of value: the consensus notebook (it is 15 of the top
20, so it is what the ladder actually pairs us against), tetsuya's
fertilizer-heavy variant, and ReCurSiON's 14-hand high-water variant. Anything
beyond those three is re-implementing the same agent.

## The last day was still farming, not liquidating

Spotted by Meet in a v24 replay against Rakhansyah: on days 29 and 30 the farm is
still watering wheat that cannot reach yield before the season ends. Correct, and
the mechanism is worse than the symptom.

Two separate faults, both provable from the engine:

1. **HARVEST was withheld until max yield.** The gate was `age >= harvest_age or
   held >= max_yield`, with `endgame` as the only override -- and `endgame` is
   `step >= EPISODE_STEPS - 2`, the last **two turns of 720**. Wheat planted
   around day 25 therefore sat ripe and unpicked through the end of the game.
2. **Watering on the final day mostly cannot pay.** A plant lost to
   `consecutive_unwatered` dies in `_daily_refresh_plants`, which runs *after*
   the last sale, so `must_water` protects nothing. An ongoing crop's yield is
   credited in that same nightly refresh, so watering strawberry or tomato on
   day 29 is worth exactly zero. Only a non-ongoing crop inside its window
   converts the turn into units that can still be picked, because that bonus
   lands immediately.

Measured before the fix, over three seeds: **$5,445 of ripe crop standing in the
field and $1,451 in units' hands** at the final step, ~$6,900 a game.

Fixed with a `liquidate_days` window (default 1). Inside it, harvest anything
ripe regardless of max yield, drop `must_water` entirely, and drop watering of
ongoing crops. Half a fix moved the loss rather than removing it -- the field
emptied to $2 and units' hands *rose* to $3,372 -- so it needs the second half:

**Last train home.** On the final day a loaded unit keeps working only while it
can still get back. Once `distance to shed + 2 >= hours_left` it banks, because
anything in hand at step 720 is worth nothing.

| | before | after |
| --- | --- | --- |
| ripe left in field | $5,445 | $95 |
| carried at final step | $1,451 | $849 |

Against v24 and v23 over 24 seeds a side: **0.812 search / 0.844 held out,
+$3,234 / +$3,745** (v24 +$1,806, v23 +$5,684). `liquidate_days` 2 ties it
(0.833, +$3,849) and 3 is worse (0.812, +$3,044), so the window stays at 1.

## How cattle and crops actually compete -- and why relaxing it does nothing

Asked directly, and the answer is that they do not compete on value anywhere.
Three mechanisms split the farm, none of which weighs an animal against a crop:

1. **Position.** Empty tiles are sorted by distance to the shed; the nearest
   `n_struct` become pens and everything further out becomes crops. Livestock
   gets the inner ring by geometry, not by being worth more.
2. **Asymmetric pricing.** `crop_value` is a real model -- profit per tile-day
   *and* per action, charged against our own in-flight supply, discounted for
   cycle length and cash starvation. A pen is worth
   `max(60, animal_profit * build_fraction)`, and `build_fraction` is **0.1**.
   The pen competes for a build action at a tenth of the animal's value.
3. **The herd target never binds.** `target_cows` 14 + `target_sheep` 12 = 26,
   and we place 11. Counting what actually stopped each purchase over a game:

| blocker | share of opportunities |
| --- | --- |
| no spare pen | 36.3% |
| past `animal_last_day` (20) | 33.3% |
| cannot afford after reserves | 27.0% |
| bought | 3.5% |
| **target reached** | **never** |

**But relaxing the binding constraint does not pay**, which is the useful half.
Against v24 over 20 seeds a side:

| variant | search | holdout |
| --- | --- | --- |
| `build_fraction` 0.3 | +$745 (0.625) | +$612 (0.525) |
| `build_fraction` 0.6 | -$400 | -$442 |
| `animal_last_day` 24 | -$21 | -$241 |
| both | +$726 | +$362 (0.475) |

Nothing clears noise: the best holdout score is 0.525 on a win rate whose
interval is +/-0.19, and +$612 is 0.7% of a bank. So "no spare pen" is a blocker
that costs nothing to be blocked by, which agrees with the measured note already
in `livestock_plan` -- an empty pen is an option, and forcing more of them cost
$34,382 at `build_ahead_cover` 1.5.

**The reading.** The herd is limited by cash and by the day-20 cutoff far more
than by pens, and the 10% pen price is closer to right than it looks. Do not
re-tune these three constants; if livestock is to grow further it needs the
*cash* path opened earlier, not the pen price raised.

## Crop-side routing: two negative results and one small win

Continuing after v23. The remaining action-budget gap is crop-side -- HARVEST at
1.95 tiles a job against THUNDER's 0.91, PLANT 1.13 against 0.64, while WATER is
already level (1.59 against 1.55). Two attempts failed and are recorded so they
are not retried.

**Chaining same-tile jobs does not pay.** THUNDER clears an animal tile in one
visit -- CARE 0.16 tiles a job, COLLECT_FERTILIZER 0.14 -- where we visited the
same animal three times (1.47 and 1.14). Bonusing distance-0 jobs by a multiple
of `action_cost` moves that metric convincingly (CARE 1.47 -> 0.73 at a bonus of
30) and **still loses money**: -$5,445 against v23 at a bonus of 2.0, and the
bank falls monotonically as the bonus rises. Total walk per job barely moves
(1.55 -> 1.48) because travel is conserved -- chaining only decides which job
gets the free slot, and it spends it on the cheap one. `same_tile_bonus` stays in
`DEFAULTS` at 0.0 so the result is not rediscovered.

**A caution about the instrument.** The first sweep of this showed identical
numbers at every bonus value, because `agent` captures its params at import and
mutating `DEFAULTS` afterwards changes nothing. Sweep through `make_agent`, the
way `lab/ab.py` does, or measure a constant.

**Crew size had gone stale, and that is the win.** `max_hands` 11 was optimal on
a five-animal farm. v23 puts fifteen animals on the board, each carrying four
jobs a day, and the optimum moved to **13**:

| max_hands | vs v23, 20 seeds a side | 32 seeds a side |
| --- | --- | --- |
| 11 (v23) | +$0 | +$0 |
| **13** | **+$1,849 / +$3,209 held out** | **+$1,181 / +$2,532 held out** |
| 15 | -$3,339 | |
| 17 | -$6,389 | |

Hands cost `fib(n)` per day, so the 14th and 15th cost $610 and $987 each on
their own -- which is why the curve turns over so sharply. Searching around 13
found nothing better: `hire_value_frac` 2.2 ties it, 1.2 and `move_factor` 3.0
and 3.9 are all worse.

Shipped as v24. It is a modest gain -- ~+$2-3k against v23, against v23's own
+$28.7k over v22 -- and worth a slot mainly because it displaces v22 from the
active pair.

**The general lesson, and it will recur.** A parameter fitted before a structural
fix encodes the farm that existed then. v23 tripled the herd; the first thing to
re-check after any change that big is every parameter that was tuned against
throughput. This is trap 4 from *Where things stand* in a new costume.

## The action budget is the binding constraint (`lab/effort.py`)

Measured 2026-08-19 against replay 91537598, both seats ~3,200. Classify every
unit-action in a game as movement, idle, or work:

| | actions | moving | idle | **working** | tiles walked per job |
| --- | --- | --- | --- | --- | --- |
| THUNDER THUNDER | 6,996 | 42.3% | 16.5% | **41.2%** | **1.02** |
| HealthStone | 6,873 | 52.8% | 9.4% | 37.8% | 1.39 |
| ours (v22) | 7,042 | 55.6% | 16.9% | **27.5%** | **2.02** |
| ours (v21) | 6,979 | 56.2% | 16.4% | 27.4% | 2.05 |

We take the same number of actions and convert **1,936** into work against
THUNDER's **2,884** -- 49% more work from an identical budget. The two rivals
fail differently, so the levers are independent: THUNDER routes well, HealthStone
routes no better than us but almost never idles a unit. Both together would be
~48% working, about **3,400 productive actions, +76% on ours**.

This subsumes several things previously filed as separate problems. We harvest
203 times to their 389, feed 114 to their 312, and issue **zero** FERTILIZE
actions to their 70 -- not because those gates are mistuned but because there was
never any labour left. Fix the walking before re-tuning anything downstream of it.

## The market has depth, and it differs per product by 60x (`lab/depth.py`)

Selling adds to a shared inventory and walks the price down `above_func`. That
shape, not the base price, decides whether a product can absorb volume:

| shape | products | price after selling 400 | avg $/unit |
| --- | --- | --- | --- |
| `log` | wheat, egg | **80% of base** | 21 / 41 |
| `sqrt` | carrot, tomato | 34% / 15% | 20 / 26 |
| `linear` | strawberry, milk | floor by ~100 units | 10 / 16 |
| `sq` | wool, melon | floor by ~60 units | 21 / 67 |

Two consequences we are currently on the wrong side of:

1. **We match the top agents only where the market cannot absorb volume.** Sell
   requests: melon 112 against their 108 (parity, and melon is `sq`); wheat 215
   against 433, milk 119 against 250, wool 0 against 132. We have tuned hardest
   against a ceiling and left the ceiling-free products at half.
2. **Pricing a tile at the current price over-plants thin markets**, because the
   current price is the first unit's price. Melon's first 100 units earn $21,721;
   the next 300 earn $5,006 total. Our agent holds 21 melon tiles and unloads them
   late, walking its own price from $277 on day 21 to $4 by day 27.

Wheat is the opposite case and is chronically under-supplied by *both* farms: in
that replay it finished 436 units below equilibrium with the price risen 25 ->
46, while the two best agents on the board sold 431 and 433 into it.

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
2. **Score the candidate against them**, at 40 seeds or more. `lab/ab.py` and
   `lab/postmortem.py` enforce a **20-seed floor** (`lab.ab.MIN_SEEDS`) and raise
   anything lower, because below it the win-rate interval is wider than any
   improvement we have shipped. Twenty is the floor for a quick read; 40+ for
   anything heading to the ladder. `--allow-small` overrides it for debugging.
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

**And ranking by rating compares across eras, which is not sound while the field
is inflating.** A rating is a mark against the opponents an agent actually
played, so a submission that stopped playing on 08-15 keeps a number earned
against a 746 field, while one still playing is marked to a 778 field today. The
`--min-games` guard makes this worse rather than better: it favours agents with
long histories, which are the ones whose histories are stalest. Until this is
fixed, read `lab/benchmarks.py` output alongside each agent's *mean opponent
rating* (in the Live submissions table) and discount an old high rating
accordingly. The honest comparison is a direct local head-to-head, which is what
`lab/ab.py --opponent recent` gives.

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

- **Carrot, tomato and egg after the 1.32.7 reprice.** Nobody on the ladder grows
  any of the three, so their deficits never close and the hinge keeps paying:
  carrot $91 and tomato $241 a unit at the deficits our own games already reach,
  against wheat's $47. Naively re-pricing the planner loses $34k (above), so the
  question is not "is it worth more" -- it is -- but how to add it without the
  livestock build slipping. Probably the single largest untouched line item now.
- **Walking, ~950 productive actions a game.** The largest single gap measured
  against the ladder, and a prerequisite for most of the items below -- see *The
  action budget is the binding constraint*. Keep a unit working a compact area
  for several turns instead of sending the cheapest unit to the best-scoring job.
- **Fertiliser is switched off entirely.** Zero FERTILIZE actions; we collect 139
  and offer 138 for sale into a market we have already glutted at ~$46. Applied to
  watered wheat it is 4 units -> 6 on the same land and seed. The engine only
  grants the bonus on a day the tile was also watered, so the two are complements.
- **Wheat.** The top agents sell 433 a game; we request 215 and, on the older
  pre-forecast agent, sold 28. The market still ends hundreds of units below
  equilibrium with the price risen. Cheapest crop, fastest cycle (5 days), and
  the only one still investable after about day 24.
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
- ~~**Stranded livestock, ~$5k a game.**~~ **Closed 2026-08-19** -- the cause was
  the PLACE job vanishing when PICKUP emptied the shed, plus nothing holding a
  unit to an animal it was carrying. `validate.py` now reports no stranding.
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
  `kaggle-environments==1.32.7`, `kaggle==2.2.4`. **This is the post-rebalance
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
