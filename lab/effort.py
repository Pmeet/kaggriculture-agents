"""Where the action budget goes: moving, idling, or working.

Every unit gets one action per turn and a game is about 7,000 unit-actions, so
the action budget is a real constraint and not an accounting curiosity. Bank
margin cannot see how it is spent -- an agent that walks twice as far per job
looks merely "worse" rather than under-staffed, and every downstream symptom
(too few harvests, no fertilising, unfed animals) reads as a separate bug.

Measured 2026-08-19 against two ~3,200-rated ladder agents, this was the single
largest gap we have found: we convert 27.5% of actions into work against
THUNDER THUNDER's 41.2%, walking 2.02 tiles per job against their 1.02.

    python lab/effort.py                          # ours vs a benchmark, seed 1
    python lab/effort.py --replay replays/x.json  # both seats of a ladder replay
    python lab/effort.py --seeds 5                # average over more games
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MOVES = ("NORTH", "SOUTH", "EAST", "WEST")
HEAD = (f"{'agent':<26}{'actions':>8}{'moving':>9}{'idle':>9}{'working':>9}"
        f"{'walk/job':>10}")


def classify(actions):
    """Split an iterable of per-turn action dicts into move / idle / work counts."""
    ops = collections.Counter()
    for action in actions:
        if not isinstance(action, dict):
            continue
        units = [action.get("farmer", ["PASS"])] + list(action.get("hands") or [])
        for unit in units:
            if isinstance(unit, list) and unit:
                ops[unit[0]] += 1
    total = sum(ops.values())
    move = sum(ops[m] for m in MOVES)
    idle = ops["PASS"]
    return {"total": total, "move": move, "idle": idle,
            "work": total - move - idle, "ops": ops}


def report(row, label):
    total = max(1, row["total"])
    work = max(1, row["work"])
    print(f"{label:<26}{row['total']:>8,}{row['move'] / total:>8.1%}"
          f"{row['idle'] / total:>9.1%}{row['work'] / total:>9.1%}"
          f"{row['move'] / work:>10.2f}")


def from_replay(path):
    with open(path) as handle:
        data = json.load(handle)
    steps = data["steps"]
    names = data.get("info", {}).get("TeamNames") or ["seat 0", "seat 1"]
    print(HEAD)
    for seat in range(len(steps[-1])):
        rows = (state[seat].get("action") for state in steps)
        report(classify(rows), names[seat][:25] if seat < len(names) else f"seat {seat}")


def from_local(candidate, opponent, seeds):
    from kaggle_environments import make

    from lab.arena import normalize_spec, resolve_agent
    from lab.versions import expand

    opponent = expand(opponent)[0]
    agents = [resolve_agent(normalize_spec(candidate)), resolve_agent(normalize_spec(opponent))]
    labels = [normalize_spec(candidate)["name"], normalize_spec(opponent)["name"]]

    collected = {0: [], 1: []}
    for seed in seeds:
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run(agents)
        for seat in (0, 1):
            collected[seat].append(classify(state[seat].action for state in env.steps))

    print(HEAD)
    for seat in (0, 1):
        merged = {k: round(statistics.fmean(r[k] for r in collected[seat]))
                  for k in ("total", "move", "idle", "work")}
        report(merged, f"{labels[seat][:20]} (n={len(seeds)})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--replay", help="analyse a downloaded ladder replay instead")
    parser.add_argument("--candidate", default="main:agent")
    parser.add_argument("--opponent", default="v21",
                        help="version label, range, or module:attr")
    parser.add_argument("--seeds", type=int, default=1)
    args = parser.parse_args()

    if args.replay:
        from_replay(args.replay)
    else:
        from_local(args.candidate, args.opponent, range(1, args.seeds + 1))


if __name__ == "__main__":
    main()
