"""Coordinate-descent parameter search against a frozen opponent.

Win rate over a few dozen games is too noisy to steer on: a 24-game match has a
+/-0.19 confidence interval, which is wider than most real improvements. So the
search optimises the *paired bank margin* instead -- our bank minus the
opponent's, averaged over the same seeds played from both seats. Common random
numbers make that estimator far tighter than win rate while staying monotone in
what actually decides games. Win rate is still reported, as the acceptance check.

Search seeds and validation seeds are disjoint, because coordinate descent will
happily fit the seeds it is shown.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402

SEARCH_SPACE = {
    "target_cows": [6, 10, 14, 18],
    "target_sheep": [4, 6, 8, 11],
    "target_geese": [0, 3, 6],
    "melon_max_tiles": [8, 14, 20, 26],
    "job_weight": [0.4, 0.8, 1.4, 2.2],
    "land_weight": [0.5, 1.0, 2.0],
    "max_hands": [11, 14, 17, 20],
    "hire_money_frac": [0.08, 0.14, 0.22, 0.32],
    "move_factor": [1.5, 1.85, 2.3],
    "work_reserve": [200, 450, 900, 1600],
    "animal_reserve": [200, 500, 1000],
    "sell_floor_frac": [0.40, 0.60, 0.75],
    "max_price_impact": [0.08, 0.18, 0.32],
    "seed_buffer": [6, 10, 16],
    "expand_when_empty": [4, 8, 14],
    "wheat_buy_max_price": [40, 60, 85],
    "feed_buffer_days": [1, 2, 3],
    "cash_comfort": [1200.0, 2500.0, 5000.0],
    "starved_discount": [0.06, 0.16, 0.30],
    "action_cost_scale": [0.25, 0.5, 1.0],
    "dig_fraction": [0.25, 0.5, 0.9],
    "fertilizer_capture": [0.3, 0.6, 0.9],
    "endgame_relax_days": [1.0, 1.6, 2.5],
}


def evaluate(module, params, opponent, seeds, workers=None):
    spec = {"module": module, "attr": "make_agent", "params": params, "name": "cand"}
    if opponent == "POOL":
        # Tuning against one frozen mirror converges on beating ourselves, which
        # is not the same as beating the ladder. Scoring against a spread of
        # archetypes -- and weighting the worst case -- keeps the result general.
        from lab.pool import SEARCH_POOL, gauntlet
        mean, worst, rows = gauntlet(spec, seeds, workers=workers,
                                     pool=SEARCH_POOL, quiet=True)
        best = max(rows, key=lambda r: r.score)
        objective = 1000.0 * (mean + worst)
        best.score_mean = mean  # type: ignore[attr-defined]
        return objective, best
    report = run_match(spec, opponent, seeds, workers=workers)
    margin = report.mean_bank - report.mean_opponent_bank
    return margin, report


def search(module, opponent, seeds, passes, base, keys, workers=None, budget=None):
    best = dict(base)
    best_margin, best_report = evaluate(module, best, opponent, seeds, workers)
    print(f"start: margin {best_margin:+,.0f}  score {best_report.score:.3f}")
    started = time.time()
    evaluated = 0

    for pass_no in range(1, passes + 1):
        improved = False
        for key in keys:
            if budget and time.time() - started > budget:
                print("budget reached; stopping search")
                return best, best_margin, best_report
            options = [v for v in SEARCH_SPACE[key] if v != best.get(key)]
            for value in options:
                trial = dict(best)
                trial[key] = value
                margin, report = evaluate(module, trial, opponent, seeds, workers)
                evaluated += 1
                flag = ""
                if margin > best_margin:
                    best, best_margin, best_report = trial, margin, report
                    improved = True
                    flag = "  <-- accepted"
                print(f"  pass{pass_no} {key}={value!r:<8} margin {margin:+9,.0f} "
                      f"score {report.score:.3f}{flag}")
        print(f"pass {pass_no} done: margin {best_margin:+,.0f} "
              f"({evaluated} evals, {time.time() - started:.0f}s)")
        if not improved:
            break
    return best, best_margin, best_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="agents.v2")
    parser.add_argument("--opponent", default="agents.baseline_a:agent")
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--budget", type=float, default=None, help="seconds")
    parser.add_argument("--keys", default="", help="comma-separated subset to search")
    parser.add_argument("--base", default="{}")
    parser.add_argument("--out", default="lab/best_params.json")
    args = parser.parse_args()

    import importlib
    module = importlib.import_module(args.module)
    base = dict(module.DEFAULTS)
    base.update(json.loads(args.base))
    keys = [k.strip() for k in args.keys.split(",") if k.strip()] or list(SEARCH_SPACE)

    seeds = range(1, args.seeds + 1)
    best, margin, report = search(
        args.module, args.opponent, seeds, args.passes, base, keys,
        workers=args.workers, budget=args.budget,
    )

    changed = {k: v for k, v in best.items() if base.get(k) != v}
    print()
    print(f"best margin {margin:+,.0f}   {report.summary()}")
    print(f"changed: {json.dumps(changed, indent=2, default=str)}")

    holdout = range(1001, 1001 + args.seeds)
    _m, hold = evaluate(args.module, best, args.opponent, holdout, args.workers)
    print(f"held-out seeds: {hold.summary()}")

    with open(args.out, "w") as handle:
        json.dump({"params": {k: v for k, v in best.items() if not isinstance(v, tuple)},
                   "changed": changed,
                   "search_margin": margin,
                   "holdout_score": hold.score,
                   "holdout_margin": hold.mean_bank - hold.mean_opponent_bank},
                  handle, indent=2, default=str)
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
