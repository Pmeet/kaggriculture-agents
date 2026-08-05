# Kaggriculture Agent Workspace

Local development kit for Kaggle's two-player Kaggriculture simulation competition.

No submission or upload is performed by this repository. Uploads remain a manual step and must not be run without explicit approval.

## Quick Start

The workspace-local virtual environment is already provisioned with Kaggle CLI `2.2.4` and `kaggle-environments` `1.32.3`.

```powershell
# Run the local tests.
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# Run the project lint command.
.\.venv\Scripts\ruff.exe check .

# Run one complete 720-turn local game.
.\.venv\Scripts\python.exe -c "from kaggle_environments import make; env=make('kaggriculture', configuration={'seed': 1}, debug=True); env.run(['main.py', 'starter']); print([(s.reward, s.status) for s in env.steps[-1]])"

# Run seeds 1-3 from both seats and write reports/quick-check/{report.json,games.csv}.
.\.venv\Scripts\python.exe -m kaggriculture_harness.cli --candidate main.py --opponent starter --seeds 1 2 3 --output reports/quick-check
```

For a clean rebuild with Python 3.12.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

The direct package versions are pinned, but transitive dependencies are not locked. The full `kaggle-environments` install is retained locally for compatibility testing; the Kaggriculture agent itself uses only the Python standard library.

## Current Baseline

[`main.py`](main.py) is a deliberately simple deterministic carrot loop used to validate the entrypoint, Kaggle loader selection, and basic action contract:

- buys one carrot seed;
- plants on the current tile;
- waters daily;
- harvests at the maximum-yield day;
- sells shed inventory;
- liquidates recoverable products on actionable step 718 without overflowing the shed;
- returns the required farmer/hands/market action schema.

The integration suite also completes a full episode from both player seats. The baseline is equivalent in strength to Kaggle's built-in `starter` and is not intended to be the first competitive strategy.

## Evaluation Harness

The paired runner evaluates every seed twice, swapping the candidate between player seats. It records candidate-relative wins/losses/ties, bank margins, seat delta, action latency, validator issue counts, and completion status.

Each run writes:

- `report.json` — manifest, aggregate metrics, per-game results, Python/package versions, and SHA-256 hashes of the current single-file candidate, installed engine, and file-based opponent when applicable;
- `games.csv` — one row per game for later comparisons.

`kaggriculture_harness.actions` provides fail-closed structural checks, exact hand normalization, atomic seed reservation, the ten-market-slot rule, and an engine-backed scratch-state reducer. Unit actions are evaluated on deep copies in farmer-then-hands order, so the validator catches sequential no-ops, destructive shed overflow, and redundant fertilizer without mutating the live observation. Market validation starts from that post-unit shed, consumes sequential `SELL` availability, conservatively tracks inventory that a dynamic `BUY_PRODUCT` might add, and preserves the first ten raw slot positions with engine-inert empty-list placeholders. Fixed-price purchase affordability remains the next projection slice. The tournament runner observes and reports issues without changing the candidate's actions.

`kaggle-environments` may print unrelated OpenSpiel registration warnings during its first import. They do not affect Kaggriculture runs; rely on the test exit code and final `DONE` statuses.

## Authenticated Read Access

The Kaggle token used during setup remains in WSL at `~/.kaggle/access_token` with mode `600`; it is not copied into this repository.

Scope it to the commands inside a PowerShell `try` block, then remove it from the process environment:

```powershell
$kaggleToken = ((wsl.exe -e sh -lc 'cat "$HOME/.kaggle/access_token"') -join '').Trim()
try {
    $env:KAGGLE_API_TOKEN = $kaggleToken
    .\.venv\Scripts\kaggle.exe competitions list -s kaggriculture
} finally {
    Remove-Item Env:KAGGLE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Variable kaggleToken -ErrorAction SilentlyContinue
}
```

Useful read-only commands to place inside that `try` block:

```powershell
.\.venv\Scripts\kaggle.exe competitions files kaggriculture --format json
.\.venv\Scripts\kaggle.exe competitions submissions kaggriculture --format json
.\.venv\Scripts\kaggle.exe competitions leaderboard kaggriculture --show
.\.venv\Scripts\kaggle.exe competitions topics list kaggriculture --sort-by top
```

## Official Material

The authenticated competition download is stored locally under `competition-data/official/` and is intentionally gitignored because competition data may only be shared with participants who accepted the rules.

- `competition-data/official/AGENTS.md` — local testing and submission guide
- `competition-data/official/README.md` — full game mechanics
- [`ROADMAP.md`](ROADMAP.md) — dated competition brief, risks, strategy, and delivery plan

The current engine is also installed at `.venv/Lib/site-packages/kaggle_environments/envs/kaggriculture/`.

## Submission Gate

When explicitly authorized, a single-file submission is the root [`main.py`](main.py). A multi-file agent must be a `.tar.gz` whose archive root contains `main.py` directly, with no wrapping directory. The full bundle, including weights, must be at most 100 MiB.

Before any upload:

1. Run all tests.
2. Run paired seeds from both player seats against the current opponent suite.
3. Confirm every game ends with `DONE` and no invalid-action diagnostics.
4. Confirm maximum turn time is comfortably below one second.
5. Confirm liquidation happens by actionable step 718.
6. Inspect the exact bundle contents and size.
7. Get explicit approval to submit.
