"""Where in the game a change won or lost the money.

Every other harness here reports one number per game, so a change that gains
$8k in the opening and loses $10k in the endgame is indistinguishable from one
that does nothing. That is the shape of most real strategy changes, and it is
why "fertiliser is negative" and "melon is positive" were both true statements
about a whole game that said nothing about when to do either.

This records both banks at day boundaries and reports the margin *accumulated
within* each phase, plus the farm state at each boundary, so a result can be
read as "won the opening, lost it back after the third quadrant" rather than a
single sign.

    python lab/phases.py --variant 'v16:{"melon_first_day":0,...}' --variant 'v17:{}'
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import (  # noqa: E402
    SHARED_OBSERVATION_FIELDS,
    normalize_spec,
    resolve_agent,
)

TURNS_PER_DAY = 24
CHECKPOINTS = (10, 20, 30)


def _snapshot(main_mod, observation, seat):
    farm = observation["farms"][seat]
    info = main_mod.census(farm)
    return {
        "bank": float(farm["money"]),
        "quads": len(farm["unlocked_quadrants"]),
        "hands": len(farm["hands"]),
        "plants": len(info["plants"]),
        "animals": len(info["animals"]),
        "weeds": len(info["weeds"]),
        "empty": len(info["empty"]),
    }


def phase_play(job):
    """One episode, recording both farms at each day boundary."""
    candidate, opponent, seed, seat = job
    from kaggle_environments import make

    import main as main_mod

    agents = [None, None]
    agents[seat] = resolve_agent(normalize_spec(candidate))
    agents[1 - seat] = resolve_agent(normalize_spec(opponent))
    resolved = list(agents)

    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    resolved = [env.agents[a] if isinstance(a, str) else a for a in resolved]
    env.reset(len(resolved))

    marks = {}
    step = 0
    while not env.done:
        shared = env.state[0].observation
        day = step // TURNS_PER_DAY
        if step % TURNS_PER_DAY == 0 and day in CHECKPOINTS:
            marks[day] = (_snapshot(main_mod, shared, seat),
                          _snapshot(main_mod, shared, 1 - seat))
        actions = []
        for index, act in enumerate(resolved):
            observation = env.state[index].observation
            if index != 0:
                for field in SHARED_OBSERVATION_FIELDS:
                    if field in shared:
                        observation[field] = shared[field]
            try:
                actions.append(act(observation))
            except Exception:
                actions.append({"farmer": ["PASS"], "hands": [], "market": []})
        env.step(actions)
        step += 1

    final = env.steps[-1]
    banks = [float(s.reward) if s.reward is not None else 0.0 for s in final]
    shared = env.state[0].observation
    marks[30] = (_snapshot(main_mod, shared, seat),
                 _snapshot(main_mod, shared, 1 - seat))
    marks[30][0]["bank"] = banks[seat]
    marks[30][1]["bank"] = banks[1 - seat]
    return marks


def run(candidate, opponent, seeds, workers):
    jobs = [(candidate, opponent, seed, seat) for seed in seeds for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(phase_play, jobs, chunksize=1))


def report(name, games):
    print(f"--- {name}")
    print(f"{'phase':>12}{'our gain':>11}{'their gain':>12}{'phase margin':>14}"
          f"{'cumulative':>12}")
    previous = (0.0, 0.0)
    for day in CHECKPOINTS:
        ours = statistics.fmean(g[day][0]["bank"] for g in games)
        theirs = statistics.fmean(g[day][1]["bank"] for g in games)
        gained_us, gained_them = ours - previous[0], theirs - previous[1]
        label = f"day {previous_day(day)}-{day}"
        print(f"{label:>12}{gained_us:>11,.0f}{gained_them:>12,.0f}"
              f"{gained_us - gained_them:>+14,.0f}{ours - theirs:>+12,.0f}")
        previous = (ours, theirs)
    print()
    print(f"{'at day':>7}{'quads':>7}{'hands':>7}{'plants':>8}{'animals':>9}"
          f"{'weeds':>7}{'empty':>7}   (ours / theirs)")
    for day in CHECKPOINTS:
        a = {k: statistics.fmean(g[day][0][k] for g in games) for k in games[0][day][0]}
        b = {k: statistics.fmean(g[day][1][k] for g in games) for k in games[0][day][1]}
        print(f"{day:>7}{a['quads']:>3.1f}/{b['quads']:<3.1f}"
              f"{a['hands']:>3.0f}/{b['hands']:<3.0f}"
              f"{a['plants']:>4.0f}/{b['plants']:<3.0f}"
              f"{a['animals']:>5.0f}/{b['animals']:<3.0f}"
              f"{a['weeds']:>4.0f}/{b['weeds']:<3.0f}"
              f"{a['empty']:>4.0f}/{b['empty']:<3.0f}")
    print()


def previous_day(day):
    index = CHECKPOINTS.index(day)
    return 0 if index == 0 else CHECKPOINTS[index - 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="main")
    parser.add_argument("--opponent", default="agents.baseline_j:agent")
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--variant", action="append", default=[])
    args = parser.parse_args()

    import importlib
    module = importlib.import_module(args.module)
    seeds = range(1, args.seeds + 1)

    print(f"{args.module} vs {args.opponent}, {args.seeds} seeds x 2 seats")
    print("'phase margin' is what the phase itself earned, not the running total.")
    print()
    for spec in args.variant:
        name, _, blob = spec.partition(":")
        params = dict(module.DEFAULTS)
        params.update(json.loads(blob or "{}"))
        candidate = {"module": args.module, "attr": "make_agent",
                     "params": params, "name": name}
        report(name.strip(), run(candidate, args.opponent, seeds, args.workers))


if __name__ == "__main__":
    main()
