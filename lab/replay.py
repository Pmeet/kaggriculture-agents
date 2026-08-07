"""Analyse a downloaded Kaggle replay to learn what real opponents do.

Local opponents are all descendants of our own ideas, so they share our blind
spots. Ladder replays are the only unbiased sample of what actually beats us.
"""

from __future__ import annotations

import collections
import json
import sys

TURNS_PER_DAY = 24


def census(farm):
    counts = collections.Counter()
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                counts["empty"] += 1
            elif tile == "LOCKED":
                counts["locked"] += 1
            elif tile.get("kind") == "PLANT":
                counts[tile["crop"].lower()] += 1
            elif tile.get("kind") == "WEED":
                counts["weed"] += 1
            elif "animal" in tile:
                counts[tile["animal"].lower()] += 1
            else:
                counts[tile.get("kind", "?").lower()] += 1
    return counts


def analyse(path, focus=None):
    data = json.load(open(path))
    steps = data["steps"]
    names = data.get("info", {}).get("TeamNames", ["seat0", "seat1"])
    rewards = [s.get("reward") for s in steps[-1]]
    print(f"=== {path}")
    print(f"teams {names}  final {rewards}")

    seats = range(len(steps[-1]))
    unit_ops = {i: collections.Counter() for i in seats}
    market_ops = {i: collections.Counter() for i in seats}
    sells = {i: collections.Counter() for i in seats}
    hires = {i: 0 for i in seats}
    hands_by_day = {i: collections.Counter() for i in seats}

    for index, state in enumerate(steps):
        day = index // TURNS_PER_DAY
        for seat in seats:
            action = state[seat].get("action")
            if not isinstance(action, dict):
                continue
            units = [action.get("farmer", ["PASS"])] + list(action.get("hands") or [])
            for unit in units:
                if isinstance(unit, list) and unit:
                    unit_ops[seat][unit[0]] += 1
            for order in action.get("market") or []:
                if isinstance(order, list) and order:
                    market_ops[seat][order[0]] += 1
                    if order[0] == "HIRE":
                        hires[seat] += 1
                    elif order[0] == "SELL" and len(order) >= 3:
                        sells[seat][order[1]] += int(order[2])
        obs = state[0]["observation"]
        for seat in seats:
            hands_by_day[seat][day] = max(
                hands_by_day[seat][day], len(obs["farms"][seat]["hands"])
            )

    print()
    print(f"{'day':>4}" + "".join(f"{('seat' + str(s)):>14}" for s in seats)
          + "   (bank, hands)")
    for day in range(0, 30, 2):
        index = min(day * TURNS_PER_DAY, len(steps) - 1)
        obs = steps[index][0]["observation"]
        row = f"{day:>4}"
        for seat in seats:
            row += f"{obs['farms'][seat]['money']:>10,.0f}/{hands_by_day[seat][day]:<3}"
        print(row)

    for seat in seats:
        farm = steps[-1][0]["observation"]["farms"][seat]
        print()
        print(f"--- seat {seat} ({names[seat] if seat < len(names) else '?'}) "
              f"final ${farm['money']:,.0f}")
        print(f"    tiles {dict(census(farm))}")
        print(f"    unit actions {dict(unit_ops[seat].most_common(10))}")
        print(f"    market {dict(market_ops[seat])}  hires={hires[seat]}")
        print(f"    sell requests {dict(sells[seat].most_common())}")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        analyse(path)
        print()
