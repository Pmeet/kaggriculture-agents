"""Run one episode and print a day-by-day diagnostic trace for one seat.

This is how we find out where the money is *not* coming from: idle units,
weeds, unsold shed stock, collapsed prices, or tiles left empty.
"""

from __future__ import annotations

import collections
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import normalize_spec, resolve_agent  # noqa: E402

TURNS_PER_DAY = 24


def tile_census(farm):
    census = collections.Counter()
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                census["empty"] += 1
            elif tile == "LOCKED":
                census["locked"] += 1
            elif tile.get("kind") == "PLANT":
                census[tile["crop"].lower()] += 1
            elif tile.get("kind") == "WEED":
                census["weed"] += 1
            elif "animal" in tile:
                census[tile["animal"].lower()] += 1
            else:
                census[tile.get("kind", "?").lower()] += 1
    return census


def run(candidate, opponent, seed=1, seat=0, verbose=True):
    from kaggle_environments import make

    agents = [None, None]
    agents[seat] = resolve_agent(normalize_spec(candidate))
    agents[1 - seat] = resolve_agent(normalize_spec(opponent))

    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)

    action_counts = collections.Counter()
    market_counts = collections.Counter()
    sold_units = collections.Counter()
    sold_value = collections.Counter()
    idle_actions = 0
    total_unit_actions = 0
    hires = 0

    prev_money = None
    for i, states in enumerate(env.steps):
        s = states[seat]
        action = s.action if isinstance(s.action, dict) else {}
        if action:
            units = [action.get("farmer", ["PASS"])] + list(action.get("hands", []) or [])
            for unit_action in units:
                op = unit_action[0] if isinstance(unit_action, list) and unit_action else "?"
                action_counts[op] += 1
                total_unit_actions += 1
                if op in ("PASS",):
                    idle_actions += 1
            prices = states[0].observation["market"]["prices"]
            for order in action.get("market", []) or []:
                if isinstance(order, list) and order:
                    market_counts[order[0]] += 1
                    if order[0] == "HIRE":
                        hires += 1
                    elif order[0] == "SELL" and len(order) >= 3:
                        # Requested, not necessarily filled; good enough to see
                        # which products the money actually comes from.
                        sold_units[order[1]] += int(order[2])
                        sold_value[order[1]] += int(order[2]) * prices.get(order[1], 0)

        if verbose and i % TURNS_PER_DAY == 0 and i < len(env.steps) - 1:
            obs = states[0].observation
            farm = obs["farms"][seat]
            census = tile_census(farm)
            priv = states[seat].observation["private"]
            shed = {k: v for k, v in priv["shed"].items() if v > 0}
            prices = obs["market"]["prices"]
            day = i // TURNS_PER_DAY
            money = farm["money"]
            delta = "" if prev_money is None else f" ({money - prev_money:+,.0f})"
            prev_money = money
            interesting = {k: v for k, v in census.items() if k not in ("locked",)}
            print(
                f"day {day:>2} ${money:>9,.0f}{delta:<12} "
                f"quads={len(farm['unlocked_quadrants'])} "
                f"tiles={dict(sorted(interesting.items()))} "
                f"shed={shed}"
            )
            if day % 6 == 0:
                print(f"        prices={ {k: v for k, v in prices.items()} }")

    final = env.steps[-1]
    print()
    print(f"FINAL  seat {seat}: ${final[seat].reward:,.0f}   "
          f"opponent ${final[1 - seat].reward:,.0f}   "
          f"status={final[seat].status}/{final[1 - seat].status}")
    obs = env.steps[-1][0].observation
    priv = env.steps[-1][seat].observation["private"]
    leftover = {k: v for k, v in priv["shed"].items() if v > 0}
    print(f"unsold shed at end: {leftover}")
    print(f"final tiles: {dict(tile_census(obs['farms'][seat]))}")
    print(f"final prices: {dict(obs['market']['prices'])}")
    print(f"market inventory: {dict(obs['market']['inventory'])}")
    print(f"town shops: {obs['town']['unlocked_shops']}")
    print()
    print(f"unit actions ({total_unit_actions} total, {idle_actions} PASS = "
          f"{100 * idle_actions / max(1, total_unit_actions):.0f}% idle):")
    for op, n in action_counts.most_common():
        print(f"   {op:<20}{n:>7}")
    print(f"market orders: {dict(market_counts)}  (hires={hires})")
    print("revenue attribution (requested sells at quoted price):")
    for item, value in sold_value.most_common():
        print(f"   {item:<12}{sold_units[item]:>7} units  ~${value:>10,.0f}")
    return env


if __name__ == "__main__":
    cand = sys.argv[1] if len(sys.argv) > 1 else "agents.v1:agent"
    opp = sys.argv[2] if len(sys.argv) > 2 else "starter"
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run(cand, opp, seed=seed)
