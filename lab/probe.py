"""Step a real episode and dump the agent's internal job list at chosen turns.

Used to answer "why did it not do X" without adding prints to the agent.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def probe(module_name, seed=1, watch_days=(1, 5, 12), seat=0, kinds=None):
    import importlib

    from kaggle_environments import make

    mod = importlib.import_module(module_name)
    params = dict(mod.DEFAULTS)
    watch = set(watch_days)

    def instrumented(obs):
        step = obs.get("step", 0)
        day = step // mod.TURNS_PER_DAY
        hour = step % mod.TURNS_PER_DAY
        action = mod._play(obs, params)
        if obs["player"] == seat and day in watch and hour in (2, 10):
            farm = obs["farms"][seat]
            info = mod.census(farm)
            hours_left = mod.TURNS_PER_DAY - hour - 1
            jobs, crop_choice, crop_score = mod.build_jobs(
                obs, farm, obs["private"], params, len(farm["tiles"]),
                day, hours_left, False, info, farm["money"],
            )
            action_cost = mod.marginal_action_cost(
                jobs, 1 + len(farm["hands"]), hours_left, params
            )
            print(f"\n--- day {day} hour {hour}  ${farm['money']:,.0f}  "
                  f"hands={len(farm['hands'])}  empty={len(info['empty'])} "
                  f"structs={info['structure_counts']} animals={info['animal_counts']}")
            shed = {k: v for k, v in obs['private']['shed'].items() if v > 0}
            print(f"    shed={shed}  seeds="
                  f"{ {k: v for k, v in obs['private']['seeds'].items() if v > 0} }")
            counts = {}
            for j in jobs:
                counts[j["kind"]] = counts.get(j["kind"], 0) + 1
            print(f"    jobs={counts}  crop={crop_choice}@{crop_score:.0f}/tile-day "
                  f"action_cost={action_cost:.0f}")
            selected = [j for j in jobs if kinds is None or j["kind"] in kinds]
            selected.sort(key=lambda j: -j["value"])
            for j in selected[:8]:
                print(f"      {j['kind']:<20} pos={j['pos']} value={j['value']:>9.0f} "
                      f"need={j.get('need')} action={j['action']}")
            print(f"    chosen unit actions: farmer={action['farmer']} "
                  f"hands={action['hands'][:6]}")
            print(f"    market={action['market']}")
        return action

    agents = [None, None]
    agents[seat] = instrumented
    agents[1 - seat] = "starter"
    # debug=True keeps stdout un-redirected so the probe output is visible.
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    env.run(agents)
    print(f"\nfinal ${env.steps[-1][seat].reward:,.0f}")


if __name__ == "__main__":
    module = sys.argv[1] if len(sys.argv) > 1 else "agents.v2"
    days = tuple(int(d) for d in sys.argv[2].split(",")) if len(sys.argv) > 2 else (1, 5, 12)
    kinds = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    probe(module, watch_days=days, kinds=kinds)
