"""Derivative-free joint search over the agent's parameters.

`optimize.py` moves one parameter at a time, which is the wrong shape for this
problem: nearly every real finding this season has been an *interaction*. The
horizon refinement only stops being terrible once the demand weights move with
it; the reserve is right or ruinous depending on whether income arrives as a
lump; `plant_commitment_cost` is fine at 42 until melon stops carrying the
economy. Coordinate descent walks into those as a wall, one axis at a time.

So: a (1+lambda) evolutionary search that perturbs a random *subset* of
parameters together, which lets a pair move jointly even when neither helps
alone. No gradients, no dependencies, and the objective is allowed to be as
noisy as it really is.

Three things keep it honest.

* The incumbent is re-evaluated every generation on the same seeds as its
  challengers, so a lucky draw cannot survive by being measured once.
* Every accepted step is validated on disjoint held-out seeds and both numbers
  are logged, so overfitting is visible while it happens rather than at the end.
* The objective is paired bank margin against a pool, not one mirror.

    python lab/evolve.py --budget 3600 --seeds 24 --out lab/evolved.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402

# (low, high, integer?) -- bounds are deliberately generous; the search is what
# decides, and a bound that is never approached costs nothing.
SPACE = {
    "target_cows": (4, 22, True),
    "target_sheep": (0, 16, True),
    "target_geese": (0, 10, True),
    "melon_max_tiles": (12, 28, True),
    "melon_first_day": (0, 20, True),
    "early_cash_tiles": (0, 25, True),
    "early_cash_last_day": (2, 16, True),
    "plant_commitment_cost": (0.0, 60.0, False),
    "job_weight": (0.2, 3.0, False),
    "land_weight": (0.1, 3.0, False),
    "move_factor": (1.2, 4.0, False),
    "max_hands": (8, 16, True),
    "hire_money_frac": (0.04, 0.5, False),
    "work_reserve": (0, 1600, True),
    "animal_reserve": (0, 1200, True),
    "reserve_frac": (0.05, 0.6, False),
    "seed_budget_frac": (0.05, 0.9, False),
    "seed_buffer": (4, 24, True),
    "expand_when_empty": (2, 24, True),
    "land_last_day": (12, 26, True),
    "animal_last_day": (14, 28, True),
    "sell_floor_frac": (0.1, 0.9, False),
    "max_price_impact": (0.05, 0.6, False),
    "endgame_relax_days": (0.6, 3.5, False),
    "cash_comfort": (500.0, 8000.0, False),
    "starved_discount": (0.0, 0.5, False),
    "discount_rate": (0.0, 0.12, False),
    "action_cost_scale": (0.1, 1.5, False),
    "dig_fraction": (0.0, 1.2, False),
    "build_fraction": (0.1, 1.5, False),
    "town_pull_weight": (0.1, 2.0, False),
    "future_pull_weight": (0.0, 2.5, False),
    "rival_supply_weight": (0.0, 1.0, False),
    "wheat_buy_max_price": (20, 100, True),
    "feed_buffer_days": (1, 4, True),
    "fertilizer_capture": (0.1, 1.0, False),
    "max_structures_ahead": (2, 8, True),
    "build_ahead_cover": (0.5, 1.2, False),
}


# Dials that only exist once `ledger_pricing` is on, added to the space only
# then. They are the ledger's analogues of the demand weights above, and the
# same argument applies with more force: the shipped weights were fitted
# against season-total pricing, so a dated model starts every one of them
# mis-fitted. `town_pull_weight` landing on 0.1 -- believe a tenth of the
# projected drain -- is the precedent worth reading before trusting 1.0 here.
LEDGER_SPACE = {
    "ledger_drain_weight": (0.05, 1.5, False),
    "ledger_rival_weight": (0.0, 1.2, False),
}


# Choices that are not numbers. `assignment_plan` is the obvious one: the letter
# for each quadrant count interacts with almost every weight, and coordinate
# descent over numbers alone cannot reach it.
CATEGORICAL = {
    "assignment_plan": ["gggg", "ggnn", "ggrr", "grrr", "gnnn", "ggrn", "grrn",
                        "gnrr", "ggnr", "gggr", "ggng", "rgrr"],
}


def mutate(params, rng, count, scale, space=None):
    """Perturb `count` parameters at once, so interacting pairs can move together."""
    space = SPACE if space is None else space
    trial = dict(params)
    for key in rng.sample(sorted(CATEGORICAL), len(CATEGORICAL)):
        if rng.random() < 0.25:
            trial[key] = rng.choice(CATEGORICAL[key])
    for key in rng.sample(sorted(space), min(count, len(space))):
        low, high, is_int = space[key]
        span = (high - low) * scale
        value = trial.get(key, (low + high) / 2)
        value = rng.gauss(float(value), max(span, 1e-9))
        value = max(low, min(high, value))
        trial[key] = int(round(value)) if is_int else round(value, 4)
    return trial


def score(module, params, opponents, seeds, workers):
    """Mean paired bank margin across the pool. Worst case breaks ties."""
    spec = {"module": module, "attr": "make_agent", "params": params, "name": "cand"}
    margins = []
    for opponent in opponents:
        report = run_match(spec, opponent, seeds, workers=workers)
        if not report.clean:
            return -1e9, -1e9
        margins.append(report.mean_bank - report.mean_opponent_bank)
    return statistics.fmean(margins), min(margins)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="main")
    parser.add_argument("--opponents", default="agents.baseline_j:agent,agents.baseline_b:agent")
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--children", type=int, default=4)
    parser.add_argument("--budget", type=float, default=1800.0, help="seconds")
    parser.add_argument("--mutate", type=int, default=3, help="params moved per step")
    parser.add_argument("--scale", type=float, default=0.18, help="step size, 0-1")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="lab/evolved.json")
    parser.add_argument("--start", default="",
                        help="JSON overrides applied to DEFAULTS as the "
                             "starting incumbent, e.g. '{\"ledger_pricing\":true}'")
    args = parser.parse_args()

    import importlib
    module = importlib.import_module(args.module)
    rng = random.Random(args.seed)
    opponents = [o for o in args.opponents.split(",") if o]

    incumbent = dict(module.DEFAULTS)
    if args.start:
        incumbent.update(json.loads(args.start))
    space = dict(SPACE)
    if incumbent.get("ledger_pricing"):
        space.update(LEDGER_SPACE)
    search = range(1, args.seeds + 1)
    holdout = range(2001, 2001 + args.seeds)

    best_mean, best_worst = score(args.module, incumbent, opponents, search, args.workers)
    print(f"start: search margin {best_mean:+,.0f} (worst {best_worst:+,.0f})")

    started = time.time()
    generation = 0
    history = []
    while time.time() - started < args.budget:
        generation += 1
        # Re-score the incumbent on the same seeds its challengers face, so a
        # value that won once by luck has to keep winning.
        best_mean, best_worst = score(
            args.module, incumbent, opponents, search, args.workers)
        improved = None
        for _ in range(args.children):
            if time.time() - started >= args.budget:
                break
            trial = mutate(incumbent, rng, args.mutate, args.scale, space)
            mean, worst = score(args.module, trial, opponents, search, args.workers)
            if (mean, worst) > (best_mean, best_worst):
                best_mean, best_worst, improved = mean, worst, trial
        if improved is None:
            print(f"gen {generation}: no improvement "
                  f"(incumbent {best_mean:+,.0f})")
            continue
        changed = {k: v for k, v in improved.items()
                   if module.DEFAULTS.get(k) != v and (k in space or k in CATEGORICAL)}
        hold_mean, _ = score(args.module, improved, opponents, holdout, args.workers)
        print(f"gen {generation}: search {best_mean:+,.0f}  held-out {hold_mean:+,.0f}"
              f"  {changed}")
        incumbent = improved
        history.append({"generation": generation, "search": best_mean,
                        "holdout": hold_mean, "changed": changed})
        with open(args.out, "w") as handle:
            json.dump({"params": {k: v for k, v in incumbent.items()
                                  if not isinstance(v, tuple)},
                       "changed_from_defaults": changed,
                       "history": history}, handle, indent=2, default=str)

    print()
    print(f"done after {generation} generations in {time.time() - started:.0f}s")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
