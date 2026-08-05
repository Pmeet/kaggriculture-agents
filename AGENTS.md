# Kaggriculture Agent Handoff

Last updated: 2026-08-05 (Asia/Calcutta)

This file is the durable handoff for any AI agent continuing work in this repository. Read it together with `README.md` and `ROADMAP.md` before editing.

## Non-negotiable constraints

- **Do not upload or submit anything to Kaggle until the user explicitly says to do so.** Local simulations and read-only Kaggle API calls are allowed. Packaging or creating a submission archive should also wait for an explicit request.
- Never print, copy into source control, or expose the Kaggle access token. Follow the scoped read-only instructions in `README.md`; the token value is intentionally not recorded here.
- Competition downloads and official files are restricted material. Keep `competition-data/` ignored and do not redistribute it.
- Keep `.kaggle/`, `.venv/`, `competition-data/`, `logs/`, `replays/`, `reports/`, and `submission*.tar.gz` out of Git.
- `main.py` must remain a self-contained Kaggle entrypoint, and `agent` must remain the last module-level callable because the Kaggle loader selects the last callable it finds.
- The runtime is offline and CPU-only. Do not add network dependencies to the submitted agent.
- Use test-driven development for every behavior change: add one failing regression, confirm the expected failure, implement the minimum fix, then run the full suite and Ruff.

## Repository snapshot

- Workspace: `D:\VS Code\Projects\kaggriculture`
- Current branch: `feature/1-correctness-harness`
- Working tree was clean before this handoff file was created.
- Current commits:
  - `0a6499c Build local Kaggriculture evaluation harness`
  - `e984fc9 Prevent sequential action and terminal inventory loss`
- No Git remote is configured (`git remote -v` is empty).
- The user authorized pushing repository changes, but did not authorize creating a GitHub repository. Ask for the remote URL or explicit permission to create a private repository before adding one.
- No Kaggle submission or upload has been made.

## Environment and verified baseline

- Windows PowerShell workspace with `.venv`.
- Python: 3.12.13.
- `kaggle-environments`: 1.32.3.
- Kaggle CLI: 2.2.4.
- Last full verification: **55 tests passed**, Ruff passed, and `pip check` reported no broken requirements.
- Last paired smoke test: six games (`main.py` versus built-in `starter`, seeds 1–3 from both seats), all six reached `DONE`, all tied, and the validator reported zero issues.
- The first `kaggle-environments` import prints large unrelated OpenSpiel registration warnings. They are harmless here; use process exit codes and final game statuses.

Verification commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m kaggriculture_harness.cli --candidate main.py --opponent starter --seeds 1 2 3 --output reports\handoff-check
git diff --check
git status --short --branch
```

The smoke report is local and ignored. Confirm `all_done_games == 6` and `total_issue_count == 0` in its `report.json`.

## What is implemented

### Competition research and roadmap

- `ROADMAP.md` contains the dated competition brief, official rules, mechanics, risks, submission contract, evaluation protocol, and phased strategy.
- `README.md` contains setup, authenticated read-only access, local evaluation, official material locations, and the manual submission gate.
- Official downloaded material is under ignored `competition-data/official/`.

### Baseline agent

- `main.py` is a deterministic carrot-loop baseline used to prove loader and engine correctness.
- It buys, plants, waters, harvests, and sells carrots.
- On actionable step 718 it performs capacity-safe liquidation.
- When shed capacity is contested, a bounded multiple-choice optimizer selects feasible `DROP`/`PLACE` actions across farmer and hands using observed prices, without overflowing the 100-item shed.
- Tests cover full shed, partial placement, unsellable inventory, higher-value allocation, quantity-aware allocation, and cross-unit capacity optimization.

### Evaluation harness

- `kaggriculture_harness/tournament.py` runs every seed twice with swapped seats.
- Results are candidate-relative and include wins/losses/ties, bank margin, seat delta, Wilson interval, action latency, completion status, and validator issue counts.
- JSON/CSV reports include Python/package versions and SHA-256 hashes for the candidate, installed engine, and file opponent when applicable.
- Candidate and file-opponent source are snapshotted before a run. Report writing rejects candidate or engine changes after the run.
- `kaggriculture_harness/cli.py` is the command-line entrypoint.

### Action validation

- `kaggriculture_harness/actions.py` validates action structure, types, arity, products, exact hand count, movement bounds, ten market slots, terminal purchases, and atomic seed overcommitment.
- Unit actions are dry-run on deep copies in exact farmer-then-hands order using the pinned engine's `_apply_unit_action`.
- The live observation is never mutated.
- Sequential no-ops are detected, including shared-tile and shared-shed conflicts.
- Destructive `DROP` overflow and redundant fertilizer are reported as `LOSSY`.
- `guard_action` fails closed and reprojects later units after suppressing a no-op or lossy action.
- The tournament currently **observes** issues but does not replace the candidate's returned action with `guard_action`.

## Current limitations and known gaps

Phase 1 remains in progress. The next important gap is state-aware market projection.

1. Market orders are structurally normalized, but their sequential effect is not projected.
2. `guard_action` currently removes malformed market entries. This compacts the first ten slots and can change alignment with the opponent's same-index orders. A faithful guard should preserve an invalid slot as an inert placeholder such as `[]` rather than shifting later orders.
3. `SELL` availability should start from the **post-unit** scratch shed, so same-turn `DROP`/`PLACE` can enable a sale.
4. Dynamic `SELL` and `BUY_PRODUCT` prices can depend on the opponent's simultaneous orders. Never declare affordability from the displayed price alone after money becomes opponent-dependent.
5. Fixed-price `BUY_SEED` and `BUY_ANIMAL`, plus `HIRE` and `BUY_LAND`, can be projected exactly while money is known.
6. Partial `PICKUP`, `PLACE`, and `SELL` requests leave the remainder at the source; they are not destructive losses. Prefer a distinct `PARTIAL` severity if this is added rather than mislabeling them `LOSSY`.
7. Terminal `PLACE` classification is still broad. At step 718 it should be considered useful only when the resolved branch deposits a sellable item into the shed.
8. Real replay-derived observation fixtures, the broader engine regression matrix, and the 1,000-game reliability soak remain undone.

## Exact next TDD slice

No market-projection production code or tests were started before this handoff. Start with a small vertical slice and keep the public APIs unchanged:

```python
inspect_action(obs, action) -> tuple[Issue, ...]
guard_action(obs, action) -> dict
```

Recommended red tests, one at a time:

1. A `SELL CARROT 1` with an empty initial shed is valid when the farmer performs a same-turn valid `DROP` containing one carrot.
2. A `SELL` with zero post-unit availability reports a guaranteed `NO_OP` and is removed or replaced with an inert slot by the guard.
3. A `SELL` quantity greater than known post-unit availability reports a non-destructive partial fulfillment without labeling the remainder lost.
4. A malformed order in market slot 0 does not shift a valid order from slot 1 in guarded output.
5. A fixed-price `BUY_SEED` with definitely insufficient known money reports a `NO_OP`.
6. Two fixed-price purchases are evaluated sequentially against the same projected money balance.
7. `HIRE` reports a `NO_OP` when known money is below the exact Fibonacci-based cost.
8. `BUY_LAND` reports a `NO_OP` when all quadrants are unlocked or known money is below the next NE → SW → SE cost.
9. A dynamic-price order that could become affordable because of opponent activity is not reported as a guaranteed no-op.

Suggested implementation direction:

- Refactor the existing unit dry-run to return its post-unit scratch `farm` and `private` state alongside per-unit outcomes.
- Feed that projected state into a market reducer that processes only the first ten raw slots in index order.
- Preserve slot positions in guarded output.
- Track money as exact while only fixed-price deterministic operations occur.
- After opponent-sensitive sale revenue or dynamic `BUY_PRODUCT` pricing, track a conservative interval/unknown state and only emit a no-op when failure is guaranteed for every possible value.
- Keep opponent market inventory effects out of exact claims unless proven invariant.

Do not attempt to recreate the entire concurrent market engine in the first test cycle. Land the guaranteed `SELL` availability and slot-fidelity slice first, run the full suite, then add fixed-cost affordability.

## Engine semantics that matter for the next agent

- Unit phase runs before market phase.
- Farmer runs first, then hands in observation order.
- Atomic `PLANT` demand is checked before unit execution; overcommitting a crop suppresses all requests for that crop.
- Market processes at most the first ten raw slots per player.
- Each list index is paired with the opponent's same index.
- `HIRE` and `BUY_LAND` are handled atomically in player order at that index.
- `SELL`/`BUY_*` orders then execute unit-by-unit in lockstep; both players are quoted from the same pre-commit market inventory for each unit.
- `SELL` is guaranteed to stop when the player's shed item reaches zero, independently of opponent activity.
- `BUY_SEED` and `BUY_ANIMAL` have fixed unit costs.
- `BUY_PRODUCT WHEAT/FERTILIZER` uses dynamic prices.
- Market purchases can make the shed exceed its nominal capacity; the engine does not enforce the 100-item cap for buys.
- Unit actions cannot use a hand hired in the same turn because hiring happens after the unit phase.

The installed reference implementation is:

```text
.venv/Lib/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py
```

Treat it as the source of truth and keep `kaggle-environments` pinned. Do not edit files inside `.venv`.

## Git and handoff procedure

- Continue on `feature/1-correctness-harness` unless the user changes scope.
- Preserve unrelated user changes.
- Before every commit, run the full suite, Ruff, `pip check`, `git diff --check`, and a staged token-pattern scan.
- Commit focused checkpoints locally.
- Push is currently blocked by the missing remote. Do not create a repository without explicit user direction.
- Never stage ignored competition data, reports, virtual environments, credentials, or submission archives.
- Update this file, `README.md`, and `ROADMAP.md` when the implementation boundary changes.

## Submission gate

Local completion does not authorize a Kaggle upload. A future agent must stop before any command equivalent to `kaggle competitions submit`, candidate upload, or submission-archive publication and obtain the user's explicit approval.
