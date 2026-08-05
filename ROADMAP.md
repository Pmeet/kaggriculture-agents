# Kaggriculture Competition Brief and Roadmap

Snapshot date: **August 4, 2026**. Kaggle can change rules, deadlines, and the engine, so re-check the official pages and staff announcements before every submission window.

## Executive Summary

Kaggriculture is a two-player, 720-turn farming simulation. The winner is the agent with more money in the bank at the end; unsold inventory is worthless. Agents operate separate farms but share a dynamic market, so the opponent's visible production and selling behavior directly changes our economics.

This is a code submission competition, not a prediction-file competition. A submission is `main.py` with an `agent(obs)` function, or a `.tar.gz` with `main.py` at the archive root. Evaluation is CPU-only, offline, and limited to a 100 MiB bundle.

The right objective is **paired win rate across a diverse opponent pool**, not average final coins or winning margin. Kaggle's rating update uses only win/loss/tie and opponent strength.

No upload or submission has been made. The current account has joined the competition, has no submissions, and had all five daily slots available at this snapshot.

## Live Competition Snapshot

| Item | Verified value |
| --- | --- |
| Sponsor / host | Google LLC / Kaggle |
| Prize pool | $50,000; places 1–10 receive $5,000 each |
| Start | July 29, 2026 |
| Entry and team-merger deadline | September 23, 2026 at 23:59 UTC / September 24 at 05:29 IST |
| Final submission deadline | September 30, 2026 at 23:59 UTC / October 1 at 05:29 IST |
| Post-deadline games | Approximately October 1–15, or until convergence |
| Team size | Maximum 5 |
| Submission limit | 5 per team per day |
| Active/final agents | Latest 2 submissions |
| Teams on August 4 | 1,024 |
| Our account | Entered; 0 submissions; rank 0; 5 slots available |
| Ladder leader at snapshot | Subin An, rating 2922.0; this is volatile |

Official pages: [description](https://www.kaggle.com/competitions/kaggriculture/overview/description), [timeline](https://www.kaggle.com/competitions/kaggriculture/overview/timeline), [evaluation](https://www.kaggle.com/competitions/kaggriculture/overview/evaluation), [rules](https://www.kaggle.com/competitions/kaggriculture/rules), and [prizes](https://www.kaggle.com/competitions/kaggriculture/overview/prizes).

## What Is Actually Submitted

The competition download contains only two documentation files—`AGENTS.md` (13,057 bytes) and `README.md` (21,917 bytes). There is no CSV, hidden test set, or sample submission. The executable environment is distributed through `kaggle-environments`.

The agent receives:

```python
{
    "player": 0,
    "step": 0,
    "day": 0,
    "hour": 0,
    "farms": [...],   # both public farms
    "market": {...},  # shared inventory and prices
    "town": {...},    # shared unlocked shops
    "private": {...}, # only our shed, seeds, and worker inventories
}
```

It must return:

```python
{
    "farmer": ["OP", ...],
    "hands": [["OP", ...], ...],
    "market": [["OP", ...], ...],
}
```

Important packaging details:

- `main.py` must be at the submission or archive root.
- The intended `agent` should be the last callable exposed by `main.py`; the environment loader selects the last callable it finds.
- Files are mounted under `/kaggle_simulations/agent/`; all imports and paths must work there.
- The whole bundle, including model weights, must fit within 100 MiB.
- Do not rely on network calls or external services at runtime.

Official source: [environment README](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/README.md), [agent guide](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/AGENTS.md), [JSON schema](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.json), and [engine](https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py).

## Runtime and Evaluation

| Constraint | Value |
| --- | --- |
| Match length | 720 recorded turns, 30 days × 24 turns |
| Last actionable observation | Step 718; step 719 is terminal |
| Per-turn allowance | 1 second |
| Cumulative overage bank | 60 seconds |
| Compute | 1.6 vCPUs, CPU only |
| RAM | 6.5 GiB |
| Disk | 8 GiB |
| Network | None |
| Submission size | 100 MiB total |
| Market orders | First 10 per player per turn; extras silently dropped |

Each upload first plays self-play as a validation episode. A valid bot receives a default rating and joins similar-skill matchmaking. Only the latest two submissions remain tracked, while the leaderboard displays the better one. Newer agents receive more games. After submissions close, Kaggle continues games for about two weeks and then runs one Bradley–Terry tournament over the episode results. There is no private leaderboard.

See the [official final-evaluation announcement](https://www.kaggle.com/competitions/kaggriculture/discussion/731587) and [staff runtime clarification](https://www.kaggle.com/competitions/kaggriculture/discussion/731810).

## Rules That Affect Engineering Decisions

- One Kaggle account per person and one team per participant; maximum team size is five.
- Every member must enter individually before joining or merging. Complete any merge before September 23.
- Private code/data sharing is limited to the official team. Public code sharing must follow the competition rules and use an approved open-source license in Kaggle's public competition channels.
- External data, pretrained models, and tools are permitted only when equally accessible/reasonable and properly licensed. Runtime remains offline, CPU-only, and size-limited.
- Competition data may be used for competition, research, and education, but must not be redistributed to people who have not accepted the rules. That is why `competition-data/` is gitignored.
- Winning submissions must be licensed under CC BY 4.0 and accompanied by reproducible code and a technical description.
- Eligibility, sanctions, tax, employment, and prize-verification provisions in the full rules still apply.

## Game Mechanics That Matter Most

1. **Action economy is the core constraint.** Every farmer/hand gets one physical action per turn. Movement, planting, care, collection, and harvesting all consume actions; market orders do not consume the farmer action.
2. **Hiring is extremely cheap early each day.** Hire prices follow a Fibonacci sequence and reset daily, but hands disappear at day end. Worker routing and task assignment should be solved jointly.
3. **Plant on day and water immediately.** A new plant starts with one missed-watering count. Missing the planting-day watering can turn it into a weed at that day's refresh.
4. **The market is adversarially shared.** Opponent production is public, though its shed is private. Infer likely future sales from farm state and avoid selling premium goods into a visible glut.
5. **Premium products are fragile.** Strawberry, melon, milk, and wool can crash to the $1 floor quickly. Staggering, diversification, and opponent-aware liquidation matter more than static gross margin.
6. **Town demand is an observable price catalyst.** Shops unlock every three days and drain specific goods on a schedule. Shift production and sales based on the actual unlocked set.
7. **Inventory capacity is real.** The shed holds 100 non-seed items; end-of-day overflow is discarded. Worker inventories do not safely bypass the cap.
8. **Endgame cash is absolute.** Harvest, return/drop inventory when needed, and sell by step 718. A profitable crop still in the field or shed scores zero.

## Known Engine Risks

The current package is `kaggle-environments==1.32.3`, environment version `0.1.0`. Kaggle was still rolling fixes and investigating discrepancies on August 4.

| Issue | Current status | Engineering response |
| --- | --- | --- |
| Hands could spawn trapped on locked tiles | Staff said fix merged August 3; current source permits movement across locked tiles | Retain regression test; do not assume tile actions work while locked |
| CARE guide says +2, engine banks +1 | Unresolved | Feature-flag animal valuation; avoid depending on disputed bonus |
| Fertilizer availability/care gating differs | Unresolved | Test deployed behavior after any engine update |
| Engine currently accepts selling fertilizer while docs say it cannot be sold | Unresolved | Do not build an exploit-dependent strategy |
| Market comments refer to a 24-day calibration in a 30-day match | Unresolved | Calibrate from engine simulation rather than comments |
| Ongoing-crop/yield descriptions differ from effective caps | Under investigation | Derive economics from regression-tested engine behavior |

References: [locked-hand fix](https://www.kaggle.com/competitions/kaggriculture/discussion/731635), [documentation discrepancies](https://www.kaggle.com/competitions/kaggriculture/discussion/732450), and [open rule questions](https://www.kaggle.com/competitions/kaggriculture/discussion/731953).

Do not optimize around an unresolved discrepancy. Pin the local version, rerun the regression matrix after upgrades, and check staff posts before promoting a candidate.

## Target Agent Architecture

| Layer | Responsibility |
| --- | --- |
| State adapter | Normalize the observation and derive day/turn, owned assets, crop ages, task deadlines, and opponent production |
| Legality guard | Produce schema-valid actions, prevent atomic over-planting, cap market orders at 10, and avoid silent no-ops |
| Task scheduler | Assign farmer/hands to movement, watering, feeding, harvest, inventory, weeds, and construction |
| Farm planner | Choose crop/animal portfolio, land expansion, structures, fertilizer, and daily labor level |
| Market planner | Estimate marginal execution prices, town demand, opponent supply, sale timing, and liquidity needs |
| Opponent model | Classify visible strategy and forecast harvest/sale windows without using hidden information |
| Endgame controller | Stop long-horizon investments, harvest reachable value, return inventory, and liquidate by step 718 |
| Telemetry | Count invalid/no-op actions, missed care, overflow, latency, inventory value, and paired outcomes locally |

Keep the first competitive versions deterministic and standard-library-only. Add search or a compact learned policy only after the scheduler, market simulator, and regression suite are trustworthy.

## Evaluation Protocol

Primary metric: **paired win rate**, with the same seed played from both seats. Final bank is diagnostic only.

Opponent suite:

- built-ins: `pass`, `random`, and `starter`;
- archived versions of our own agent;
- scripted archetypes: staple spam, melon/premium, livestock, mixed portfolio, early land, and market timer;
- distilled policies from public top-rated replays, kept separate from the test suite used to tune them.

Every candidate report should include:

- wins/losses/ties and a 95% confidence interval;
- both-seat results and seat delta;
- final bank distribution and worst decile;
- action latency p50/p95/max;
- validation errors, invalid actions, and silent no-op count;
- weeds, escaped animals, discarded overflow, and unsold end inventory;
- head-to-head results against the current two promoted candidates.

Promotion gates:

1. Zero crashes/timeouts across at least 1,000 full games.
2. No malformed actions or more than 10 market orders.
3. Worst-case local action time below 250 ms, targeting p95 below 20 ms.
4. No systematic shed overflow or endgame inventory.
5. Statistically credible improvement in paired win rate, not merely higher average coins.
6. Self-play completes cleanly—the exact first server validation.

## Delivery Roadmap

### Phase 0 — Access and wiring, August 4–5

Status: **complete locally**.

- Authenticated account and competition entry verified.
- Official rules/pages and both downloadable files read.
- Kaggle CLI `2.2.4` and environment `1.32.3` installed in `.venv`.
- Root `main.py` and unit tests created.
- Full 720-turn runs complete from both seats.
- Current baseline ties the built-in starter on three paired seeds and finishes cleanly against random.
- No submission made.

### Phase 1 — Correctness harness, August 5–8

Status: **in progress locally**.

Completed in the first slice:

- paired-seat tournament runner with candidate-relative outcomes and seat delta;
- JSON/CSV reports with action latency, issue counts, package version, and engine/candidate hashes;
- fail-closed structural action guard covering hand counts, operation shape, market limits, and atomic seed overcommitment;
- farmer-then-hands scratch-state validation for sequential unit no-ops, shed overflow, and redundant fertilizer;
- post-unit market projection for guaranteed empty `SELL` orders, conservative conditional-product ranges, and first-ten slot fidelity;
- capacity-safe step-718 drop/place-and-sell behavior in the baseline.

Remaining:

- Build observation fixtures from real replays.
- Extend market projection through fixed-price affordability while keeping opponent-dependent money conservative.
- Tighten terminal `PLACE` classification and non-destructive partial-request reporting.
- Add environment regression tests for watering, crop production, workers, market execution, overflow, and step-718 liquidation.
- Run and archive the 1,000-game reliability soak.

Exit gate: 1,000 error-free baseline games, reproducible reports, and complete action/latency telemetry.

### Phase 2 — Strong deterministic baseline, August 9–16

- Expand beyond one tile with a grid route planner.
- Hire and schedule workers daily without duplicate/atomic plant failures.
- Compare wheat/carrot/melon and mixed portfolios under labor and price constraints.
- Add weed clearing, inventory return, land-purchase ROI, and explicit endgame mode.
- Create conservative and aggressive scripted opponents.

Exit gate: materially better than `starter` in paired play—target at least 80% decisive win rate over 200+ paired games—and no regression in reliability.

### Phase 3 — Dynamic market and opponent response, August 17–30

- Reproduce the exact unit-by-unit concurrent order processor locally.
- Forecast town consumption from unlocked shops and clock.
- Infer opponent harvest windows and likely shed pressure from public tiles.
- Optimize order splitting/timing and avoid premium-product floors.
- Add portfolio switching and cash-reserve rules for land, animals, feed, and workers.
- Mine the [daily top episodes dataset](https://www.kaggle.com/datasets/kaggle/kaggriculture-episodes-index) for strategy archetypes, not as an unbiased sample.

Exit gate: positive paired win rate across all scripted archetypes and improved worst-decile bank without exploit dependence.

### Phase 4 — Planning and policy optimization, August 31–September 13

- Add short-horizon lookahead for worker assignment and market timing.
- Evaluate beam search, dynamic programming, or a small offline-trained policy under the CPU/time budget.
- Use common-random-number experiments and ablations for every feature.
- Maintain two complementary branches: robust/conservative and adaptive/aggressive.

Exit gate: each promoted feature shows a repeatable win-rate lift against held-out seeds and archived agents; p95 latency stays well below one second.

### Phase 5 — Robustness and team freeze, September 14–22

- Decide team composition early enough to merge before September 23.
- Freeze environment-facing APIs and submission layout.
- Run thousands of games across both seats and adversarial scenarios.
- Simulate timeouts, missing optional keys, large inventories, locked tiles, and extreme price floors.
- Audit licenses and ensure the bundle can be released under winner obligations.
- Select two finalists and one rollback candidate.

Exit gate: two reproducible, complementary agents with zero critical failures and documented bundle hashes.

### Phase 6 — Submission window, September 23–30

This phase remains blocked until explicit user approval to upload.

- Use one slot for server validation, then inspect its self-play episode and logs.
- Never consume all five daily slots with minor variants.
- Remember that uploading a third candidate removes the oldest of the latest two from active tracking.
- Promote only after local paired evaluation; label every submission with version and hash.
- Upload finalists early enough to recover from packaging/runtime errors, not in the final minutes.
- Ensure the latest two on September 30 are exactly the intended finalists.
- Stop long-running experiments before the deadline and preserve a known-good rollback.

### Post-deadline — October 1–15

- No more submissions; monitor episode health and final convergence.
- Respect the 3,600 `ListEpisodes` views per rolling 24 hours confirmed by staff.
- Prefer sampled diagnostics and the official daily replay dataset over exhaustive polling.
- Archive exact source, bundle, environment version, reports, and licenses for potential winner verification.

Staff references: [episode-view quota](https://www.kaggle.com/competitions/kaggriculture/discussion/732114), [daily replay announcement](https://www.kaggle.com/competitions/kaggriculture/discussion/731215), and [official Discord/forum guidance](https://www.kaggle.com/competitions/kaggriculture/discussion/730708).

## Immediate Next Work

The next implementation slice remains correctness work, not a sophisticated policy:

1. Project fixed-price `BUY_SEED`, `BUY_ANIMAL`, `HIRE`, and `BUY_LAND` affordability in raw market-slot order.
2. Tighten terminal `PLACE` classification and report partial requests without calling them destructive.
3. Add replay-derived observation fixtures and the broader engine regression matrix.
4. Run the 1,000-game reliability soak and archive its reproducibility metadata.
5. Then implement a multi-tile worker scheduler and beat `starter` reliably before requesting a Kaggle slot.

This ordering makes every later strategy experiment measurable and keeps server submissions for decisions that local evidence supports.
