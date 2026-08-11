# Kaggriculture Agent Handoff

Last updated: 2026-08-11 (Asia/Calcutta)

Durable handoff for any agent continuing this work. Read with `README.md` and
`ROADMAP.md`.

## Non-negotiable constraints

- The user granted **standing authority to submit** on 2026-08-07 ("don't need to
  ask me for submissions if you decide it's worth it"). Judgement still applies:
  five slots a day, only the latest two stay active, so submit when local
  evidence says a candidate beats the live one.
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

`main.py` is a livestock-led economy. Against the built-in `starter` it banks
about $100k to `starter`'s $3.5k; the pre-existing carrot-loop baseline tied
`starter` at $3,498.

| Opponent | Record (80 paired games) | Bank |
| --- | --- | --- |
| `starter` | 80-0 | $99,566 vs $3,495 |
| `random` | 80-0 | $99,706 vs $12 |
| `agents/v1.py` (crop-only) | 80-0 | $81,386 vs $48,661 |
| `agents/baseline_a.py` (first submission) | 71-9 | $76,967 vs $51,454 |

Two submissions are live. Ratings converge over hours, so read them late.

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

## Research loop (`lab/`, never submitted)

- `arena.py` — paired matches from both seats. `fast_play` skips the framework's
  per-step deep copy (over half a game's runtime) and is pinned to `env.run` by
  `tests/test_integration.py`.
- `pool.py` — the opponent gauntlet, including archetypes reconstructed from
  real ladder replays.
- `optimize.py` — coordinate descent on paired bank margin, or on the pool.
- `economics.py`, `inspect_game.py`, `probe.py`, `replay.py` — analysis.

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

## Open leads

- **Herd size.** Across six ladder games we lost every game where the opponent
  accumulated more animal-days (452, 338, 330) and won every game where they
  accumulated fewer (0, 0, 112). Locally, forcing a larger herd loses, because
  milk and wool crash and our own extra supply cannibalises our existing sales.
  Unresolved: whether animal-days are the cause or a symptom of a stronger early
  economy. This is the most valuable open question.
- Placing every owned animal is **not** automatically right — stranded stock was
  accidentally protecting us from crashing wool. Fix the buying decision rather
  than forcing placement.
- Melon still sells into its own crash; sale pacing across days is unexplored.
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
