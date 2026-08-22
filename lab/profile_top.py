"""One row per top-ladder agent: what its farm looks like and how it spends turns.

The point is variety, not a single exemplar. Reading one replay tells you what
that agent did; reading twenty tells you which choices are consensus at the top
and which are one team's idea -- and only the consensus ones are worth copying.
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
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

TPD = 24
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
ANIMAL_OPS = {"FEED", "CARE", "COLLECT_FERTILIZER"}
TOP = os.path.join(REPO, "replays", "top")


def profile(steps, seat):
    ops = collections.Counter()
    sells = collections.Counter()
    plants = collections.Counter()
    pend = collections.defaultdict(int)
    walk = collections.defaultdict(lambda: [0, 0])
    for i, state in enumerate(steps):
        if i % TPD == 0:
            pend.clear()
        action = state[seat].get("action")
        if not isinstance(action, dict):
            continue
        units = [action.get("farmer", ["PASS"])] + list(action.get("hands") or [])
        for ui, unit in enumerate(units):
            if not (isinstance(unit, list) and unit):
                continue
            op = unit[0]
            ops[op] += 1
            if op in MOVES:
                pend[ui] += 1
                continue
            if op == "PASS":
                continue
            if op == "PLANT" and len(unit) > 1:
                plants[unit[1]] += 1
            grp = "animal" if op in ANIMAL_OPS else "other"
            walk[grp][0] += 1
            walk[grp][1] += pend[ui]
            pend[ui] = 0
        for order in action.get("market") or []:
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
                sells[order[1]] += int(order[2])

    final = steps[-1][0]["observation"]["farms"][seat]
    tiles = collections.Counter()
    animals = 0
    for row in final["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t:
                    animals += 1
                    tiles[t["animal"]] += 1
                elif t.get("kind") == "PLANT":
                    tiles[t["crop"]] += 1
                elif t.get("kind") == "WEED":
                    tiles["WEED"] += 1
    peak_hands = max(len(steps[min(d * TPD + 12, len(steps) - 1)][0]
                         ["observation"]["farms"][seat]["hands"]) for d in range(30))
    total = max(1, sum(ops.values()))
    work = total - sum(ops[m] for m in MOVES) - ops["PASS"]
    return {
        "bank": steps[-1][seat].get("reward") or 0,
        "actions": total,
        "move_pct": 100 * sum(ops[m] for m in MOVES) / total,
        "idle_pct": 100 * ops["PASS"] / total,
        "work_pct": 100 * work / total,
        "walk_per_job": (sum(ops[m] for m in MOVES) / max(1, work)),
        "animal_walk": walk["animal"][1] / max(1, walk["animal"][0]),
        "hands": peak_hands,
        "animals": animals,
        "quads": len(final["unlocked_quadrants"]),
        "water": ops["WATER"], "harvest": ops["HARVEST"], "plant": ops["PLANT"],
        "fert": ops["FERTILIZE"], "feed": ops["FEED"], "care": ops["CARE"],
        "dig": ops["DIG"], "build": ops["BUILD_PASTURE"] + ops["BUILD_COOP"],
        "sells": sells, "plants": plants, "tiles": tiles,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dir", default=TOP)
    args = parser.parse_args()

    index = {}
    idx_path = os.path.join(args.dir, "index.json")
    if os.path.exists(idx_path):
        index = json.load(open(idx_path))

    rows = []
    for fn in sorted(os.listdir(args.dir)):
        if not fn.endswith("-replay.json"):
            continue
        eid = fn.split("-")[1]
        data = json.load(open(os.path.join(args.dir, fn)))
        names = data.get("info", {}).get("TeamNames") or ["seat0", "seat1"]
        for seat in (0, 1):
            p = profile(data["steps"], seat)
            p["name"] = names[seat] if seat < len(names) else f"seat{seat}"
            p["rating"] = index.get(eid, {}).get("rating")
            rows.append(p)

    seen = {}
    for r in rows:
        if r["name"] not in seen or r["bank"] > seen[r["name"]]["bank"]:
            seen[r["name"]] = r
    rows = sorted(seen.values(), key=lambda r: -r["bank"])

    print(f"{'agent':<22}{'bank':>9}{'hnd':>4}{'anml':>5}{'q':>2}"
          f"{'work%':>7}{'wlk/job':>8}{'anmwlk':>7}"
          f"{'water':>6}{'harv':>6}{'plnt':>6}{'fert':>5}{'dig':>5}")
    for r in rows:
        print(f"{r['name'][:21]:<22}{r['bank']:>9,.0f}{r['hands']:>4}{r['animals']:>5}"
              f"{r['quads']:>2}{r['work_pct']:>7.1f}{r['walk_per_job']:>8.2f}"
              f"{r['animal_walk']:>7.2f}{r['water']:>6}{r['harvest']:>6}"
              f"{r['plant']:>6}{r['fert']:>5}{r['dig']:>5}")

    print()
    print("consensus (median across agents):")
    for key in ("bank", "hands", "animals", "quads", "work_pct", "walk_per_job",
                "water", "harvest", "plant", "fert", "dig"):
        vals = [r[key] for r in rows]
        print(f"   {key:<14}{statistics.median(vals):>10,.1f}"
              f"   range {min(vals):,.0f} - {max(vals):,.0f}")

    print()
    print("crops planted (times), summed across agents:")
    agg = collections.Counter()
    for r in rows:
        agg.update(r["plants"])
    for k, v in agg.most_common():
        print(f"   {k:<12}{v:>7}  ({v / len(rows):.1f} per agent)")
    print()
    print("sell requests, summed:")
    agg = collections.Counter()
    for r in rows:
        agg.update(r["sells"])
    for k, v in agg.most_common():
        print(f"   {k:<12}{v:>7}  ({v / len(rows):.0f} per agent)")


if __name__ == "__main__":
    main()
