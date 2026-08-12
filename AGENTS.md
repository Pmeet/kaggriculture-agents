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

Read 2026-08-12 10:07 UTC. Two slots left today.

- **v17 (55455741)** — shop-led economy: wheat opening, melon deferred to day 12,
  `plant_commitment_cost` 8. Validated, seeded 600. Submitted at the user's
  direction *knowing it measures -$29,476 held out*, to test whether a local
  mirror can fairly judge an opening built for shop demand.
- **v16 (55452371)** — melon cap 20 + opponent-supply-aware planting. 721.6 and
  climbing from 600.
- v15 (753.5 over ~20 games) has dropped out of active tracking; it is frozen at
  `agents/baseline_j.py` and remains the control every A/B is run against.

**If v17 rates below ~650, restore v15 from `agents/baseline_j.py`.** It is the
strongest agent measured to date and only two uploads separate it from being
active again.

## Melon is the capital pump, not a crop

This is the finding that governs the whole opening, and it is the reason four
separate attempts to diversify have each cost $25-48k a game.

Melon is a *bad product*: no shop demands it, the town drains exactly 30 units a
season, and selling a harvest visibly craters the price from $250 to $100. All
of that is true and none of it matters. Melon's job is to convert ten days of
otherwise-idle opening land into **one lump of cash on day 11**, while livestock
still has 18 days left to compound it.

| | 20 melon tiles | 16 melon tiles |
| --- | --- | --- |
| bank, day 11 | **$5,632** | $3,805 |
| herd, day 12 | 7 cows, 7 sheep | 4 cows, 0 sheep |
| herd, day 20 | 10 cows, 7 sheep | 6 cows, 2 sheep |
| final bank | $88,921 | $49,253 |

$1,800 less on day 11 is the difference between buying the herd outright and
buying one cow, and the farm never catches up, because `animal_last_day` and the
compounding window do not move. Everything that trims melon below ~19 tiles hits
this cliff regardless of *why* it trimmed:

| lever | held-out margin |
| --- | --- |
| `melon_max_tiles` 16 | -$39,118 |
| `max_crop_share` 0.45 | -$49,575 |
| `demand_floor` 0.85 (a 15% tilt) | -$34,307 |
| `early_cash_tiles` 6 | -$10,364 |

**So diversifying the opening needs another source of day-11 capital first.**
That is the actual open problem, not a better argument for diversifying. Until
one exists, the levers stay switched off in `DEFAULTS` with their numbers.

### Animals can be removed after all

An earlier note here said placed animals are stuck. They are not, and the
difference matters: two consecutive missed feeds and `_daily_refresh_animals`
deletes the animal **and leaves the pasture or coop standing**. Starving an
animal is therefore a deliberate two-day way to recycle a pen into one whose
product the shops actually want. Not yet implemented; it is the obvious answer
to the stranded-livestock waste and to a herd built for demand that never came.

### The flat planting charge forbids short crops

`plant_commitment_cost` charges a fixed amount per follow-up job a planting
commits to. At 42 that is $252 against wheat's $260 cycle, so a wheat tile was
worth $8 while walking one step cost $9 -- short-cycle crops were unplantable,
and no measurement showed it because melon carried the economy and never needed
them. At 8 wheat sales go from 28 a game to 312. Note it measures *worse* in the
melon economy (bank up $5k, margin down $7k), so it belongs with the shop-led
opening, not on its own.

One related trap: demand coverage must never touch livestock. Tilting toward the
best-covered product concentrated the herd into 14 cows and 2 sheep instead of
7 and 7, costing $37k -- milk and wool are both thin markets that floor after
40-60 surplus units, so spreading across two beats picking the better one.
`animal_profit` already prices each animal against its own product's supply.

## The engine was rebalanced -- pin 1.32.6

The ladder runs **kaggle-environments 1.32.6**, not the 1.32.3 this repo was
originally pinned to. Confirmed from a live replay of our own submission:
`townCenterSellInterval: 24` and `unlocked_shops` containing duplicates. If a
result looks impossible, check the engine version first.

Crops, animals and the price curve are **unchanged**. What changed:

- Town centre drains 1 unit per product every 24 turns, flat. The old rising
  multiplier (2x after day 10, 4x after day 20) is gone. **Melon demand fell from
  ~140 units a season to exactly 30** -- no shop demands melon.
- Shops are drawn **with replacement**, capped at 8 instances, so a season can
  contain four pizza shops and no yarn store. Expected season demand and its
  spread (400 sampled seasons): wheat 523 (318-696), strawberry 422 (210-624),
  milk 331 (138-534), carrot 312 (84-570), wool 246 (30-534), egg 225 (66-390),
  tomato 222 (30-390), melon 30 (fixed), fertilizer 0.
- Shed operations (PICKUP / DROP / shed-PLACE) resolve **before** the LOCKED
  guard, so all four shed-access tiles work from turn one.
- `BUY_PRODUCT` and `BUY_ANIMAL` now respect `shedCapacity`.

That per-game demand spread is the standing opportunity: the shops are public,
and the published meta analysis shows most top players running fixed hardcoded
routes that cannot react to them.

## What the engine actually does

The prose docs disagree with the engine in several places. The engine at
`.venv/Lib/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`
is the source of truth, and `tests/test_agent.py` pins our copies of its
constants and price curve against it.

- Animals produce their base unit **even when unfed**. Feeding matters for
  survival (two consecutive missed feeds and the animal is gone) and to bank the
  `CARE` bonus, which is **+1 per day**, not +2.
- `FERTILIZER` **can be sold**, and no town building consumes it, so it is a
  pure glut pot of roughly $25k shared between both players. Every living animal
  yields one per day for one action.
- Tile operations bail out early on `LOCKED` tiles -- but shed operations are
  now checked *first*, so `PICKUP`/`DROP` work from all four access tiles. This
  was the opposite on 1.32.3 and is the single most version-sensitive behaviour
  in the agent.
- The unit phase runs before the market phase, so anything a hand picks up this
  turn has already left the shed when the sell orders execute.
- Over-committing `PLANT` for a crop makes the engine drop **every** `PLANT` for
  that crop that turn.
- Market purchases now respect `shedCapacity` too; end-of-day drops discard the
  overflow.

## The economics that drive the design

Derived from the engine by `lab/economics.py`, not from the docs.

- **Labour is nearly free.** Hire cost is `fib(n)` and resets daily: ten hands
  cost $143 for ~230 extra actions. Actions and market liquidity bind, not land.
- **The town still under-supplies premium goods**, so strawberry, milk and wool
  trade well above base. But post-rebalance the totals are lower and vary hugely
  per season (see the demand table above), so read `town.unlocked_shops` rather
  than assuming a fixed figure.
- **Glut curves differ enormously.** Wheat and egg are logarithmic and absorb
  effectively unlimited volume (~$19 / ~$38). Strawberry, milk and wool collapse
  to the $1 floor after 40-60 units above equilibrium. Melon is `sq`-shaped: very
  valuable in small quantity, worthless in bulk.
- **Livestock dominates per tile and per action.** Feed, care, harvest and
  fertilizer collection all happen on one tile, so a move amortises over four
  jobs, and animals need no watering. A cared-for cow returns roughly $415 a day
  against its $400 price.
- **Melon is load-bearing.** Removing it collapses the gauntlet score from 0.898
  to 0.062. Do not "simplify" it away.

## The demand forecast

`town_pull` used to count only shops that had already unlocked. On day 0 -- the
turn that decides what fills the farm -- none have, so every crop was priced
against three days of town-centre drain and wheat looked worthless.

The shops a season contains are unknowable, but their distribution is not: one
unlocks every 3 days up to 8 instances, each a uniform draw **with replacement**
from the 8 shop types. So a product's expected demand from a future unlock is
its share of the pool — wheat is in 5 of 8 shops, strawberry 4, melon 0.
Projecting that reproduces the empirically sampled season demand to within 6%
with no fitted constant, and `tests/test_agent.py` pins both the schedule and
the prior against the engine.

`future_pull_weight` belongs at exactly 1.0 — "believe the pool average". It is
sharply non-monotonic: 1.5 costs $6.3k, because over-crediting future wheat
demand hands it the whole farm and melon monoculture beats that.

## Agent architecture (`main.py`)

Every job is valued **in dollars** and assigned by `value - distance *
action_cost`, where `action_cost` is the marginal job dropped for lack of
capacity. Pricing a walk at its real opportunity cost keeps units working the
tile in front of them and makes assignments stable across turns.

- `census` — one board pass everything else reads.
- `build_jobs` — livestock, weeds, crops, and filling empty tiles.
- `assign_units` — greedy matching, with reservations for seeds and shed stock.
- `plan_market` — one budget spent in payback order: feed, livestock, seed, land.
- `plan_sales` — sells down to each product's own collapse point, capped by
  price impact, relaxing to a full liquidation as the season closes.

## Reading the ladder (all read-only, all unauthenticated except the CLI)

Rating and rank:

```bash
KAGGLE_API_TOKEN="$(cat ~/.kaggle/access_token)" ~/.venvs/kaggri/bin/kaggle \
    competitions submissions kaggriculture
KAGGLE_API_TOKEN="$(cat ~/.kaggle/access_token)" ~/.venvs/kaggri/bin/kaggle \
    competitions leaderboard kaggriculture --download -p .
```

Our episodes, with each opponent's rating and both banks -- this is what the
0.54 above came from. The endpoint takes **`submissionId`** or **`ids`**; a
`teamId` filter is rejected, and `ids` must all belong to one competition:

```bash
curl -sS -X POST \
  https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes \
  -H "Content-Type: application/json" --data-binary '{"submissionId":55428714}'
```

Replays of the **top** agents come from the official daily datasets, not from
the API -- `GetEpisodeReplay` is gone. `kaggle/kaggriculture-episodes-index`
lists one dataset per day, each ~21 GB of episodes named `<episodeId>.json`, and
these are top-tier games (median avg rating ~3,080). List the filenames, run the
ids through `ListEpisodes` to find the strongest pairing, then pull that one
file:

```bash
kaggle datasets files kaggle/kaggriculture-episodes-2026-08-10 --page-size 400
kaggle datasets download kaggle/kaggriculture-episodes-2026-08-10 -f 91537598.json -p replays/
~/.venvs/kaggri/bin/python lab/replay.py replays/91537598.json
```

Staff cap `ListEpisodes` at 3,600 views per rolling 24 hours.

## Research loop (`lab/`, never submitted)

- `arena.py` — paired matches from both seats. `fast_play` skips the framework's
  per-step deep copy (over half a game's runtime) and is pinned to `env.run` by
  `tests/test_integration.py`.
- `ab.py` — the workhorse now the pool is saturated. Plays named parameter
  variants against a frozen snapshot over search seeds *and* disjoint held-out
  seeds, and reports paired bank margin for each. Read the held-out column.
- `pool.py` — the opponent gauntlet, including archetypes reconstructed from
  real ladder replays. Use it as a regression check, not as a steering signal.
- `optimize.py` — coordinate descent on paired bank margin, or on the pool.
- `economics.py`, `inspect_game.py`, `probe.py`, `replay.py` — analysis.
  `replay.py` reads both our episodes and downloaded ladder replays.

**Measurement discipline that has repeatedly mattered:**

1. Win rate over a few dozen games has a ±0.19 interval. Steer on paired bank
   margin, and confirm with head-to-head.
2. Always validate on held-out seeds. Opponent-supply weighting looked like
   +0.16 on search seeds and +0.05 on held-out.
3. Tuning against one frozen mirror converges on beating ourselves. Use the pool.
4. A parameter tuned around a bug encodes the bug. When livestock accounting was
   fixed, every herd-size setting had to be retuned.
5. Check whether a cap is actually binding before tuning it. `max_hands` was
   raised from 14 to 26 with *identical* results, because the workload estimate
   feeding it was the real limit.
6. Absolute bank against `starter` is not a competitive signal. Work-in-passing
   lifted it 20% and measured neutral-to-negative head to head, because the
   market is uncontested against a trivial opponent.

## Mechanical edges found by measurement, not reasoning

Every large win so far came from a silent loss or an engine detail, never from
strategy tuning. Look here first.

- **Market orders resolve by index**, each player's order i quoted against the
  same pre-commit inventory. Selling at index 0 rather than 5 is worth ~11% on a
  premium sale ($12,817 vs $11,530 on 40 melons). Sells go first, ordered by
  price impact.
- **End-of-day drops discard anything past the shed cap**, and produce sitting
  in unit inventories is invisible to the shed-level guard. Was costing ~$5.5k a
  game in melon and milk; now $37.
- **The workload estimate, not `max_hands`, sets the workforce.** The cap never
  bound; `move_factor` did.
- **Locked shed tiles** swallowed PICKUP/DROP on the old engine and no longer do.

## Why the fourth quadrant never opens, and why that is correct

Traced day by day (seed 1, v17). The 4th quadrant costs $4,000 and needs
$4,450 free after `work_reserve`:

| day | bank | blocked by |
| --- | --- | --- |
| 0-21 | $94 - $2,172 | **cash** -- the farm is fully invested, never idle |
| 22 | $14,174 | **`land_last_day: 20`** |
| 25 | $25,962 | `land_last_day: 20` |
| 29 | $51,768 | `land_last_day: 20` |

The bank crosses the price on day 22; the gate closes on day 20. We are never
both solvent and allowed. That looks like an obvious bug and it is not: every
route to opening it measures negative.

| change | held-out margin vs not doing it |
| --- | --- |
| `land_last_day` 26 | -$5,779 |
| `land_last_day` 24 + land bought before livestock | -$6,106 |
| land bought before livestock | -$448 (neutral) |
| `expand_when_rich` 4000 | -$3,486 |

A quadrant bought on day 22 has eight days to work. Strawberry needs ten to
first yield, a cow eight before its first milk and then two-day intervals. The
tiles cannot mature, so $4,000 of score buys less than $4,000 of produce.

**Final cash is the score** -- reward is `farm["money"]`, and unsold stock is
worth nothing. So $50k sitting in the bank on day 29 is not idle capital, it is
fifty thousand points. Spending it late is only right when the return lands
before the whistle, which is exactly what `land_last_day` and `animal_last_day`
encode. The real constraint is not late-game spending, it is that income before
day 20 is too small; that is where work belongs.

## Hiring more hands is arithmetically impossible

Hire prices are `fib(n)` and **reset every day**, so the cost of running a
workforce is the cumulative sum, every day:

| hands | per day | over 30 days | the last hand alone |
| --- | --- | --- | --- |
| 10 | $231 | $6,930 | $89 |
| 14 | $1,595 | $47,850 | $610 |
| 18 | $10,944 | $328,320 | $4,181 |
| 26 | $514,227 | $15,426,810 | $196,418 |

`max_hands: 14` is not a conservative cap, it is near the edge of what the
economy can pay for. Measured at 26 it costs -$53,648 and the bank falls from
$54,096 to $30,594. Weeds are the same story from the other side: `dig_fraction`
1.0 measures -$679, because the actions are worth more elsewhere.

## Labour capacity is real, and pricing it a third time does not help

`labour_saturation` reports jobs owed over jobs reachable, and it confirms what
a replay looks like: the farm sits at **0.98-1.34 from day 16 onward** while
holding $14k-$49k, and the weed count spikes to 11-13 in exactly that window. So
the farm genuinely cannot work what it owns, and keeps buying more.

Gating the budget on it -- stop buying seed, animals and land above the slack
line -- measures neutral to negative in every form tried, on the *healthy* v16
economy (the v17 opening is too weak to read a second effect through):

| variant | held-out margin | score |
| --- | --- | --- |
| no gate | -$697 | 0.475 |
| hard gate at 1.00 | -$1,873 | 0.400 |
| hard gate at 1.05 | -$2,730 | 0.338 |
| labour priced by scarcity, k=1 | +$5 | 0.512 |
| labour priced by scarcity, k=3 | -$1,680 | 0.400 |
| fertilise once saturated | -$2,384 | 0.375 |

The reason is that labour is already charged for twice. `crop_value` divides a
crop by the jobs its cycle will consume (`job_weight`), which is the buying-side
price; `marginal_action_cost` prices every walk at the value of the job dropped
for want of capacity, which is the routing-side price. A third capacity signal
double-counts what those two already say, and a hard gate replaces a smooth
price with a cliff. Note a 24-seed run showed the gate at +$798 and 40 seeds
turned it to -$1,873 -- trap 1 in the list below, caught by widening the sample.

Kept as `capacity_slack` / `job_weight_scarcity`, both off, because the
saturation number itself is the useful part: it is the honest way to see whether
a change bought work the farm can actually do.

## Fertilizer is free and still not worth applying

The input costs nothing -- every animal drops one a day and we collect ~193 a
game -- so this looks like an easy win, and the engine's own table backs it: one
fertilizer is +2 strawberry, ~$570 at real prices, against a ~$50 sale.

It measures negative anyway, and the reason is actions, not dollars. Fertilizing
displaces watering *and then demands more of it*, because an ongoing crop only
banks the bonus on a day it is also watered. One game, fertiliser always on
against off:

| | off | always |
| --- | --- | --- |
| FERTILIZE actions | 0 | 58 |
| WATER actions | 534 | **412** |
| strawberry sold | 136 | **116** |
| bank | $68,526 | $53,568 |

58 fertilizes cost 122 waterings and produced *fewer* strawberries. The promised
bonus is never collected because the watering that would collect it is the thing
that got crowded out.

**`fertilize_min_edge` is a multiplier on the fertilizer price, not a dollar
amount.** An earlier sweep of 0/60/200 was really testing always/never/never and
concluded nothing; swept properly the result is monotone -- always -$10,819,
edge 1 -$5,041, edge 4 -$2,739, edge 16 -$749, off -$697 -- so less is always
better. Check what a threshold is denominated in before sweeping it.

## Targeting fertiliser and care at what the town wants

`demand_coverage` now returns a raw share in [0, 1] -- 1.0 is the most-wanted
product this season, 0.0 one no shop will ever ask for -- and it tracks the
actual draw: a yarn+carrot season reads wool 0.91 and milk 0.27, a
milk+strawberry one reads milk 0.82 and wool 0.18. Callers compress it to taste.

Gating **fertiliser** on it is directionally right and still not enough:

| variant | held-out margin |
| --- | --- |
| fertilise, ungated | -$5,041 |
| fertilise only where coverage >= 0.6 | -$4,205 |
| fertilise only where coverage >= 0.8 | -$2,721 |
| do not fertilise | **-$697** |

Targeting recovers about half the loss, and the trend keeps converging on off.

Gating **CARE** the same way is actively harmful: -$4,533 at a 0.35 floor and
-$25,018 at 0.55. CARE banks +1 per production day and is the main multiplier on
the whole herd, and coverage measures *relative* demand -- milk at 0.27 still
sells near $290. Never withhold care from an animal that is producing.

## The board is small: nothing is far away

The shed access tiles are the four in the centre, (4,4) (5,4) (4,5) (5,5), and
the quadrants radiate out from them. **The farthest tile on the whole board is 8
steps from a shed**, and the distance histogram is 4/8/12/16/20/16/12/8/4 tiles
at 0-8 steps.

So capping how far out we will plant does nothing until it starts discarding
usable land: radius 10 and 8 play byte-identical games to unlimited, radius 6
costs -$9,344 and radius 4 costs -$15,872. "The far edge of the third quadrant"
is eight steps from the shed. Movement is ~55% of unit-turns because the work is
spread over up to 100 tiles that all lead back to one central shed, which is
board geometry, not a placement mistake.

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
