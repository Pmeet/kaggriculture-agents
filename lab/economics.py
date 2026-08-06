"""Derive the strategic decision table straight from the installed engine.

Everything here reads engine constants and replays engine functions rather than
the prose docs, because the two disagree in several places (animal production
while unfed, sellable fertilizer, care bonus size).
"""

from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/parekhmeet/.venvs/kaggri/lib/python3.12/site-packages")

from kaggle_environments.envs.kaggriculture import kaggriculture as K  # noqa: E402

TURNS_PER_DAY = 24
DAYS = 30


def crop_cycle(crop: str, fertilize: bool = False) -> dict:
    """Simulate one plant->harvest cycle for a single tile, engine-faithfully.

    Returns the best (yield, cycle_days, water_actions) plan: water on the
    planting day (mandatory, the plant starts at consecutive_unwatered=1), keep
    it alive on alternate days, and water every day inside the bonus window.
    """
    cd = K.CROPS[crop]
    if cd["ongoing"]:
        return ongoing_cycle(crop, fertilize)

    window_start = (cd["max_yield_day"] + 1) // 2
    best = None
    for harvest_day in range(cd["first_yield_day"], cd["max_yield_day"] + 1):
        # Days we must water to avoid weeds: day 0, then no two consecutive misses.
        watered = {0}
        day = 0
        while day < harvest_day:
            # Water inside the bonus window for yield; otherwise only as needed.
            nxt = day + 1
            if window_start <= nxt <= min(harvest_day, cd["max_yield_day"]):
                watered.add(nxt)
                day = nxt
                continue
            if nxt + 1 > harvest_day:
                break
            watered.add(nxt + 1)  # skip one day, water the next
            day = nxt + 1
        bonus_days = sum(1 for d in watered if window_start <= d <= cd["max_yield_day"])
        per_day = 2 if fertilize else 1
        units = min(cd["max_yield"], 1 + bonus_days * per_day)
        cycle_days = max(1, harvest_day)  # replant on the harvest day itself
        actions = 1 + len(watered) + 1  # plant + waters + harvest
        rate = units / cycle_days
        cand = {
            "crop": crop,
            "harvest_day": harvest_day,
            "units": units,
            "cycle_days": cycle_days,
            "waters": len(watered),
            "actions": actions,
            "units_per_tile_day": rate,
            "actions_per_unit": actions / units,
            "seed_cost": cd["seed"],
        }
        if best is None or cand["units_per_tile_day"] > best["units_per_tile_day"]:
            best = cand
    return best


def ongoing_cycle(crop: str, fertilize: bool = False) -> dict:
    """Ongoing crops fire `max_yield` scheduled productions then decay."""
    cd = K.CROPS[crop]
    productions = cd["max_yield"]
    per_production = 2 if fertilize else 1
    units = productions * per_production
    last_day = cd["first_yield_day"] + (productions - 1) * cd["interval"]
    # Alive-watering every other day, plus watering on each production day for
    # the fertilizer bonus; approximate with every-day watering when fertilizing.
    waters = last_day + 1 if fertilize else math.ceil(last_day / 2) + 1
    actions = 1 + waters + productions  # plant + waters + harvests
    return {
        "crop": crop,
        "harvest_day": last_day,
        "units": units,
        "cycle_days": last_day + 1,
        "waters": waters,
        "actions": actions,
        "units_per_tile_day": units / (last_day + 1),
        "actions_per_unit": actions / units,
        "seed_cost": cd["seed"],
    }


def animal_plan(animal: str, place_day: int = 0, care: bool = True) -> dict:
    """Replay the engine's daily animal refresh to count product + fertilizer."""
    a = K.ANIMALS[animal]
    tile = K._new_animal(animal, place_day)
    farm = {"tiles": [[tile]]}
    produced = 0
    fertilizer = 0
    actions = 0
    wheat = 0
    for day in range(place_day, DAYS):
        # Daily labour: FEED (needs 1 wheat), CARE, HARVEST, COLLECT_FERTILIZER.
        if tile.get("fertilizer_available"):
            fertilizer += 1
            tile["fertilizer_available"] = False
            actions += 1
        if tile.get("yield_units", 0) > 0:
            produced += tile["yield_units"]
            tile["yield_units"] = 0
            actions += 1
        tile["fed_today"] = True
        wheat += 1
        actions += 1
        if care:
            tile["cared_today"] = True
            actions += 1
        K._daily_refresh_animals(farm, day)
        tile = farm["tiles"][0][0]
        if "animal" not in tile:
            break
    produced += tile.get("yield_units", 0)
    return {
        "animal": animal,
        "cost": a["cost"],
        "product": a["product"],
        "units": produced,
        "fertilizer": fertilizer,
        "wheat_consumed": wheat,
        "actions": actions,
        "days": DAYS - place_day,
        "units_per_day": produced / (DAYS - place_day),
    }


def sell_revenue(item: str, quantity: int, start_inventory: int | None = None) -> tuple[float, int]:
    """Exact engine revenue for dumping `quantity` units, unit by unit."""
    inv = K.MARKET_I0 if start_inventory is None else start_inventory
    revenue = 0.0
    for _ in range(quantity):
        price = K.market_price(item, inv)
        revenue += price
        if price > 1:
            inv += 1
    return revenue, inv


def buy_cost(item: str, quantity: int, start_inventory: int | None = None) -> tuple[float, int]:
    inv = K.MARKET_I0 if start_inventory is None else start_inventory
    cost = 0.0
    for _ in range(quantity):
        cost += K.market_price(item, inv - 1)
        inv -= 1
    return cost, inv


def liquidity_table() -> list[dict]:
    """How much can be sold before the marginal price collapses."""
    rows = []
    for item in K.PRODUCTS:
        base = K.MARKET_PARAMS[item]["base"]
        row = {"item": item, "base": base}
        for q in (50, 100, 200, 400, 800, 1600):
            row[f"p@{q}"] = K.market_price(item, K.MARKET_I0 + q)
        row["rev@200"] = sell_revenue(item, 200)[0]
        row["rev@800"] = sell_revenue(item, 800)[0]
        # Volume at which marginal price falls below half of base.
        half = max(1, base // 2)
        q = 0
        while q < 5000 and K.market_price(item, K.MARKET_I0 + q) > half:
            q += 10
        row["q_half_price"] = q
        rows.append(row)
    return rows


def town_demand(days: int = DAYS, unlock_order: list[str] | None = None) -> dict[str, int]:
    """Total units drained by shops + town center over a season."""
    demand = {item: 0 for item in K.PRODUCTS}
    shops = unlock_order or sorted(K.SHOPS)
    unlocked: list[str] = []
    for step in range(days * TURNS_PER_DAY):
        day = step // TURNS_PER_DAY
        n_unlocked = min(len(shops), max(0, day // 3))
        unlocked = shops[:n_unlocked]
        if step % 4 == 0:
            for shop in unlocked:
                products = K.SHOPS[shop]
                mult = 2 if len(products) == 1 else 1
                for item in products:
                    demand[item] += mult
        if step % 12 == 0:
            mult = next(m for t, m in K.TOWN_CENTER_DEMAND_SCHEDULE if day >= t)
            for item in K.TOWN_CENTER_PRODUCTS:
                demand[item] += mult
    return demand


def report() -> None:
    print("=" * 100)
    print("CROP CYCLES (one tile, engine-faithful watering plan)")
    print("=" * 100)
    print(f"{'crop':<12}{'harv_day':>9}{'units':>7}{'cycle_d':>9}{'u/tile/day':>12}"
          f"{'acts/unit':>11}{'seed':>7}{'$/tile/day@base':>17}")
    for crop in K.CROPS:
        for fert in (False, True):
            c = crop_cycle(crop, fert)
            base = K.MARKET_PARAMS[crop]["base"]
            gross = c["units_per_tile_day"] * base - c["seed_cost"] / c["cycle_days"]
            tag = crop + ("+fert" if fert else "")
            print(f"{tag:<12}{c['harvest_day']:>9}{c['units']:>7}{c['cycle_days']:>9}"
                  f"{c['units_per_tile_day']:>12.3f}{c['actions_per_unit']:>11.2f}"
                  f"{c['seed_cost']:>7}{gross:>17.1f}")

    print()
    print("=" * 100)
    print("ANIMALS (placed day 0, fed + cared daily, harvested + fertilizer collected daily)")
    print("=" * 100)
    for animal in K.ANIMALS:
        for care in (True, False):
            a = animal_plan(animal, care=care)
            base = K.MARKET_PARAMS[a["product"]]["base"]
            value = a["units"] * base + a["fertilizer"] * K.MARKET_PARAMS["FERTILIZER"]["base"]
            tag = animal + ("+care" if care else "")
            print(f"{tag:<12} cost={a['cost']:>4}  {a['product']:<6} units={a['units']:>3}  "
                  f"fert={a['fertilizer']:>3}  wheat={a['wheat_consumed']:>3}  "
                  f"actions={a['actions']:>3}  gross@base=${value:>7,.0f}  "
                  f"net=${value - a['cost']:>7,.0f}  $/action={value / max(1, a['actions']):>6.1f}")

    print()
    print("=" * 100)
    print("MARKET LIQUIDITY (marginal price after selling q units into a fresh market)")
    print("=" * 100)
    rows = liquidity_table()
    quantities = (50, 100, 200, 400, 800, 1600)
    header = f"{'item':<12}{'base':>6}" + "".join(f"{'p@' + str(q):>8}" for q in quantities)
    print(header + f"{'q<half':>9}{'rev@200':>11}{'rev@800':>11}")
    for r in rows:
        print(f"{r['item']:<12}{r['base']:>6}"
              + "".join(f"{r['p@' + str(q)]:>8}" for q in (50, 100, 200, 400, 800, 1600))
              + f"{r['q_half_price']:>9}{r['rev@200']:>11,.0f}{r['rev@800']:>11,.0f}")

    print()
    print("=" * 100)
    print("TOWN DEMAND over the season (units removed from market = free price support)")
    print("=" * 100)
    demand = town_demand()
    for item, units in sorted(demand.items(), key=lambda kv: -kv[1]):
        print(f"{item:<12}{units:>6} units   "
              f"(~${units * K.MARKET_PARAMS[item]['base']:,} at base price)")

    print()
    print("=" * 100)
    print("HIRE COST LADDER (resets daily)")
    print("=" * 100)
    total = 0
    for n in range(0, 18):
        total += K._hire_cost(n)
        actions = (n + 1) * 23
        print(f"  {n + 1:>2} hands/day: marginal ${K._hire_cost(n):>6,}   "
              f"cumulative ${total:>7,}   ~{actions} extra actions   "
              f"${total / max(1, actions):>6.2f}/action")

    print()
    print("=" * 100)
    print("WHEAT PURCHASE COST (animal feed) - buying drains inventory and raises price")
    print("=" * 100)
    for q in (100, 300, 600, 1000, 1500):
        cost, _ = buy_cost("WHEAT", q)
        print(f"  buy {q:>5} wheat: ${cost:>8,.0f}   avg ${cost / q:>6.1f}/unit")


if __name__ == "__main__":
    report()
