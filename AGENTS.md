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

**v15 (55450849), submitted 2026-08-12 06:31 UTC** — per-tile marginal pricing
plus the demand forecast, commit `04e3061`; frozen at `agents/baseline_j.py`.
Validated COMPLETE, seeded at 600, and 709 after three games (2W-1L).

v14 (55428714) is the other active slot, at **715 after 47 games, 23W-24L**.
It is our only converged rating, so **do not submit a third agent until v15 has
played enough games to compare** — a third upload drops v14 out of tracking and
leaves two unproven agents.

The melon-cap commit after v15 is *not* submitted; it is worth +$4,283 held out
and is the natural v16 once v15's rating settles.

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
