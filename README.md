# Kaggriculture Agent Workspace

Development kit for Kaggle's two-player Kaggriculture simulation competition.

Submissions are a manual, individually-approved step. Nothing in this repository
uploads anything on its own.

## Quick Start

The research environment is a Linux virtualenv at `~/.venvs/kaggri`
(Python 3.12.13, `kaggle-environments==1.32.7`, `kaggle==2.2.4`). That version
is the post-rebalance engine the ladder runs, and every measurement belongs
there. The Windows `.venv/` in the repository is **stale** — it is still on
1.32.3, the pre-rebalance engine, and is not a parity check. See the Environment
section of [`AGENTS.md`](AGENTS.md) for what differs and how to verify the
version from a live replay.

```bash
# Tests and lint.
~/.venvs/kaggri/bin/python -m unittest discover -s tests
~/.venvs/kaggri/bin/python -m ruff check .

# Score the submitted agent against the full opponent gauntlet.
~/.venvs/kaggri/bin/python lab/pool.py 24

# One episode with a day-by-day diagnostic trace.
~/.venvs/kaggri/bin/python lab/inspect_game.py main:agent agents.baseline_b:agent 1

# The engine-derived economics table that drives the strategy.
~/.venvs/kaggri/bin/python lab/economics.py
```

To rebuild the research environment:

```bash
uv venv --python 3.12 ~/.venvs/kaggri
VIRTUAL_ENV=~/.venvs/kaggri uv pip install "kaggle-environments==1.32.7" "kaggle==2.2.4" ruff
```

`kaggle-environments` prints unrelated OpenSpiel/CABT loader warnings on first
import. They are harmless; rely on exit codes and final `DONE` statuses.

## The Agent

[`main.py`](main.py) is a self-contained, standard-library-only agent that runs a
livestock-led farm economy. Against the built-in `starter` it banks about $100k
to `starter`'s $3.5k.

Every job — feed, care, harvest, water, plant, build, dig, place — is valued in
dollars and assigned to units by `value - distance * action_cost`, where
`action_cost` is the marginal job dropped for lack of labour. Selling replicates
the engine's price curve exactly and stops at each product's own collapse point.

The strategy follows from measurements in [`lab/economics.py`](lab/economics.py):
labour is nearly free (ten hands cost $143/day for ~230 actions), the town
drains ~3,300 units a season so premium goods trade well above base, and
livestock dominates because its four daily jobs share one tile and it needs no
watering. See [`AGENTS.md`](AGENTS.md) for the full design notes, the engine
behaviours that differ from the published docs, and the open questions.

## Research Loop (`lab/`)

Nothing under `lab/` is submitted.

| Module | Purpose |
| --- | --- |
| `arena.py` | Paired matches from both seats, in worker processes |
| `pool.py` | Opponent gauntlet, including archetypes from real ladder replays |
| `optimize.py` | Coordinate-descent parameter search |
| `economics.py` | Engine-derived crop/animal/market decision tables |
| `inspect_game.py` | Per-episode diagnostics and revenue attribution |
| `probe.py` | Dumps the agent's internal job list at chosen turns |
| `replay.py` | Analyses downloaded Kaggle replays |
| `versions.py` | Resolves `recent` / `vNN` / `vNN..vNN` to frozen snapshots |
| `checks/frozen.py` | Guards `agents/` against edits to a frozen snapshot |

`arena.fast_play` skips the framework's per-step deep copy, which profiling put
at over half a game's runtime. `tests/test_integration.py` pins it to identical
results from the official `env.run` path.

Measurement discipline, learned the hard way: win rate over a few dozen games has
a ±0.19 interval, so steer on paired bank margin and confirm head-to-head; always
validate on held-out seeds; and tune against the pool rather than a single frozen
copy of the agent.

## Branches

Each candidate agent is developed on its own branch cut from `main`
(`agent/v23`, `agent/v24`, …). Work happens in `main.py`; when a candidate is
frozen for submission it is copied to the next `agents/baseline_*.py`, recorded
in `lab/submissions.json`, and merged back to `main`.

A version branch can still be scored against every earlier agent without
switching branches, because opponents resolve as Python modules from the working
tree and all the frozen snapshots live in `agents/`:

```bash
# The last six submissions, resolved from lab/submissions.json at run time.
~/.venvs/kaggri/bin/python lab/ab.py --seeds 40 --variant 'cand:{}'
```

Two rules keep that honest. `agents/` is **append-only** — editing a frozen
snapshot silently changes what every past measurement meant, which
`lab/checks/frozen.py` exists to catch. And opponent sets are **never
hardcoded**: `recent` re-reads the registry each run, so the bar rises on its
own as versions ship. Full workflow in [`AGENTS.md`](AGENTS.md).

## Correctness Harness

`kaggriculture_harness` runs agents from files and validates their actions
against the engine's semantics — sequential no-ops, atomic seed over-commitment,
the ten-market-slot rule, destructive overflow. It is the pre-submission gate and
currently reports zero issues over full games.

## Authenticated Read Access

The Kaggle token stays in WSL at `~/.kaggle/access_token` (mode 600) and is never
copied into this repository. Scope it per command:

```bash
KAGGLE_API_TOKEN="$(cat ~/.kaggle/access_token)" \
  ~/.venvs/kaggri/bin/kaggle competitions leaderboard kaggriculture -s
```

Useful read-only commands: `competitions submissions kaggriculture`,
`competitions episodes <SUBMISSION_ID>`, `competitions replay <EPISODE_ID> -p replays`.
Downloaded replays are the only unbiased sample of what actually beats us.

## Official Material

Stored under gitignored `competition-data/official/`, since competition data may
only be shared with participants who accepted the rules.

- `competition-data/official/AGENTS.md` — local testing and submission guide
- `competition-data/official/README.md` — full game mechanics
- [`ROADMAP.md`](ROADMAP.md) — competition brief, risks, and delivery plan

## Submission Gate

A single-file submission is the root [`main.py`](main.py). A multi-file agent
must be a `.tar.gz` whose archive root contains `main.py` directly, at most
100 MiB.

Before any upload:

1. Run the tests and Ruff.
2. Run the gauntlet from both seats.
3. Confirm every game ends `DONE` with no validator issues.
4. Confirm p95 turn latency is far below one second (currently ~0.6ms).
5. Confirm nothing is left unsold in the shed at the final step.
6. Get explicit approval for that specific submission.
# kaggriculture-agents
