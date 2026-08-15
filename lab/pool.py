"""The opponent pool a candidate must beat, and the gauntlet that scores it.

Tuning against a single frozen copy of ourselves converges on a strategy that
beats *us*, which is not the same as one that beats the ladder. Ladder replays
show three recurring archetypes we never generated locally, so they are
reproduced here as parameter variants and scripted opponents.

The observation that motivated this: across six ladder games, we lost every
game where the opponent accumulated more animal-days than us (452, 338, 330 to
our 212-269) and won every game where they accumulated fewer (0, 0, 112).
"""

from __future__ import annotations

import os
import statistics
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402


def variant(params, name, module="agents.v3"):
    return {"module": module, "attr": "make_agent", "params": params, "name": name}


# Archetypes drawn from real ladder opponents.
# The two agents that have held our highest live ratings. Every future
# candidate is measured against these before anything else: they are the only
# opponents whose strength is confirmed by the ladder rather than by us.
#
#   v15 (baseline_j) -- melon capital-pump economy, peak 753.5
#   v21 (baseline_n) -- capacity-gated shop-led economy, peak 810.4
#
# They are deliberately *different economies*, not two versions of one idea, so
# beating both means beating two distinct ways of playing rather than one
# lineage with a tuning change. Keep them frozen.
#
# v21 replaced v18 (baseline_k, peak 786.5) on 2026-08-15 under the promotion
# rule: a benchmark is only displaced by an agent holding a **higher live
# rating**, never by one that merely looks better locally. v18 is kept on disk
# for reference but is no longer a yardstick.
BENCHMARKS = [
    {"module": "agents.baseline_j", "attr": "agent", "name": "v15-melon"},
    {"module": "agents.baseline_n", "attr": "agent", "name": "v21-capgated"},
]

POOL = BENCHMARKS + [
    "starter",
    {"module": "agents.v1", "attr": "agent", "name": "crop-only"},
    {"module": "agents.baseline_a", "attr": "agent", "name": "baseline_a"},
    {"module": "agents.baseline_b", "attr": "agent", "name": "baseline_b"},
    # "MD. AS-AID RAHMAN": very large mixed herd, almost no crops, no weeding.
    variant({"target_cows": 16, "target_sheep": 10, "target_geese": 4,
             "melon_max_tiles": 6, "dig_fraction": 0.0}, "big-herd-mixed"),
    # "Lando Wang": sheep-led, fertilizer-heavy.
    variant({"target_cows": 8, "target_sheep": 14, "target_geese": 0,
             "fertilizer_capture": 1.0}, "sheep-led"),
    # "Versilogic": cows plus geese, sells wheat rather than buying it.
    variant({"target_cows": 13, "target_sheep": 0, "target_geese": 10,
             "wheat_buy_max_price": 25}, "cow-goose"),
    # A crop-heavy foil, so we do not over-fit to livestock mirrors.
    variant({"target_cows": 2, "target_sheep": 1, "target_geese": 0,
             "melon_max_tiles": 30, "plant_commitment_cost": 0.0}, "crop-heavy"),
]


def gauntlet(candidate, seeds, workers=16, pool=None, quiet=False):
    """Score a candidate against every opponent; report the worst case too."""
    pool = pool or POOL
    rows = []
    for opponent in pool:
        report = run_match(candidate, opponent, seeds, workers=workers)
        rows.append(report)
        if not quiet:
            name = report.opponent
            print(f"   vs {name:<16} score={report.score:.3f} "
                  f"bank {report.mean_bank:>9,.0f} "
                  f"margin {report.mean_bank - report.mean_opponent_bank:>+9,.0f}")
    mean = statistics.fmean(r.score for r in rows)
    worst = min(r.score for r in rows)
    if not quiet:
        print(f"   MEAN {mean:.3f}   WORST {worst:.3f}")
    return mean, worst, rows


if __name__ == "__main__":
    seeds = range(1, int(sys.argv[1]) + 1) if len(sys.argv) > 1 else range(1, 25)
    candidate = {"module": "main", "attr": "agent", "name": "main"}
    print("main.py against the pool:")
    gauntlet(candidate, seeds)


# A cheaper, deliberately diverse subset for parameter search: both ladder-proven
# benchmarks, plus two archetypes that play unlike either of them.
SEARCH_POOL = BENCHMARKS + [
    next(p for p in POOL if isinstance(p, dict) and p.get("name") == "big-herd-mixed"),
    next(p for p in POOL if isinstance(p, dict) and p.get("name") == "crop-heavy"),
]
