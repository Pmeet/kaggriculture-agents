"""Run many games and ask what distinguishes the ones we lose.

A win rate is one number with a wide interval; forty-eight games cannot tell you
*why* the bad games are bad. This runs enough games that the losing tail is a
population rather than an anecdote, records a handful of observable features per
game, and reports how each feature differs between wins and losses.

It answers a different question from `lab/ab.py`. That one asks "is this change
better"; this one asks "when it is not, what is happening". Both are needed --
the objective is Pr[win] = Phi(mu/sigma), and shrinking sigma means understanding
the left tail rather than raising the average.

    python lab/postmortem.py --seeds 800 --opponent v24
"""

from __future__ import annotations

import argparse
import collections
import os
import statistics
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TPD = 24

from lab.ab import MIN_SEEDS  # noqa: E402  the one floor, defined once


def _one(job):
    """Play one game and return per-game features. Must be top-level to pickle."""
    import warnings as w
    w.filterwarnings("ignore")
    from kaggle_environments import make

    from lab.arena import normalize_spec, resolve_agent

    cand_spec, opp_spec, seed, seat = job
    agents = [None, None]
    agents[seat] = resolve_agent(normalize_spec(cand_spec))
    agents[1 - seat] = resolve_agent(normalize_spec(opp_spec))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)

    final = env.steps[-1]
    obs = final[0].observation
    farm = obs["farms"][seat]
    ours, theirs = final[seat].reward, final[1 - seat].reward

    tiles = collections.Counter()
    animals = 0
    empty_pens = 0
    for row in farm["tiles"]:
        for t in row:
            if t == "LOCKED":
                tiles["locked"] += 1
            elif t is None:
                tiles["empty"] += 1
            elif isinstance(t, dict):
                if "animal" in t:
                    animals += 1
                elif t.get("kind") == "WEED":
                    tiles["weed"] += 1
                elif t.get("kind") == "PLANT":
                    tiles["crop"] += 1
                elif t.get("kind") in ("PASTURE", "COOP"):
                    empty_pens += 1

    shops = collections.Counter(obs["town"]["unlocked_shops"])
    peak_hands = 0
    for i in range(0, len(env.steps), 6):
        peak_hands = max(peak_hands, len(env.steps[i][0].observation["farms"][seat]["hands"]))

    return {
        "seed": seed, "seat": seat,
        "bank": ours, "opp": theirs, "margin": ours - theirs,
        "win": 1 if ours > theirs else 0,
        "animals": animals, "empty_pens": empty_pens,
        "weeds": tiles["weed"], "crops": tiles["crop"], "empty": tiles["empty"],
        "quadrants": len(farm["unlocked_quadrants"]),
        "peak_hands": peak_hands,
        "shop_kinds": len(shops), "shop_max_dup": max(shops.values()) if shops else 0,
    }


FEATURES = ("bank", "opp", "animals", "empty_pens", "weeds", "crops", "empty",
            "quadrants", "peak_hands", "shop_kinds", "shop_max_dup")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--candidate", default="main:agent")
    parser.add_argument("--opponent", default="v24")
    parser.add_argument("--seeds", type=int, default=400,
                        help=f"minimum {MIN_SEEDS}; fewer decides nothing")
    parser.add_argument("--start", type=int, default=5000,
                        help="first seed; keep clear of search (1-) and holdout (1001-)")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    args.seeds = max(MIN_SEEDS, args.seeds)

    from lab.versions import expand
    opp = expand(args.opponent)[0]
    jobs = [(args.candidate, opp, s, seat)
            for s in range(args.start, args.start + args.seeds)
            for seat in (0, 1)]

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(_one, jobs, chunksize=4))

    wins = [r for r in rows if r["win"]]
    losses = [r for r in rows if not r["win"]]
    n = len(rows)
    margins = [r["margin"] for r in rows]
    mu = statistics.fmean(margins)
    sd = statistics.pstdev(margins) or 1.0
    banks = sorted(r["bank"] for r in rows)

    name = opp["name"] if isinstance(opp, dict) else opp
    print(f"{args.candidate} vs {name}: {n:,} games "
          f"(seeds {args.start}-{args.start + args.seeds - 1}, both seats)")
    print(f"  win rate {len(wins) / n:.3f}   mu {mu:>+9,.0f}   "
          f"sigma {sd:>9,.0f}   mu/sigma {mu / sd:.2f}")
    print(f"  our bank  p1 {banks[n // 100]:>8,.0f}  p10 {banks[n // 10]:>8,.0f}  "
          f"median {banks[n // 2]:>8,.0f}  p90 {banks[9 * n // 10]:>8,.0f}")
    # Seats are not symmetric -- the shed sits in one corner and both farms draw
    # from one market -- so a seat split is the first thing to check before
    # reading any feature as a cause.
    print()
    print(f"  {'seat':<14}{'games':>8}{'win rate':>10}{'mu':>11}{'median bank':>13}")
    for seat in (0, 1):
        sub = [r for r in rows if r["seat"] == seat]
        if not sub:
            continue
        sb = sorted(r["bank"] for r in sub)
        print(f"  {seat:<14}{len(sub):>8,}"
              f"{statistics.fmean(r['win'] for r in sub):>10.3f}"
              f"{statistics.fmean(r['margin'] for r in sub):>+11,.0f}"
              f"{sb[len(sb) // 2]:>13,.0f}")

    print()
    print(f"  {'feature':<14}{'in wins':>11}{'in losses':>11}{'gap':>11}")
    for f in FEATURES:
        won = statistics.fmean(r[f] for r in wins) if wins else 0.0
        lost = statistics.fmean(r[f] for r in losses) if losses else 0.0
        print(f"  {f:<14}{won:>11,.1f}{lost:>11,.1f}{won - lost:>+11,.1f}")

    print()
    worst = sorted(rows, key=lambda r: r["margin"])[:8]
    print("  worst games:")
    for r in worst:
        print(f"    seed {r['seed']}/{r['seat']}  margin {r['margin']:>+9,.0f}  "
              f"bank {r['bank']:>8,.0f} v {r['opp']:>8,.0f}  animals {r['animals']:>2} "
              f"pens {r['empty_pens']:>2} weeds {r['weeds']:>2} crops {r['crops']:>2} "
              f"hands {r['peak_hands']:>2}")


if __name__ == "__main__":
    main()
