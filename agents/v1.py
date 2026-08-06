"""Kaggriculture v1: multi-tile, multi-hand crop economy.

Design notes (measured against the installed engine, see ``lab/economics.py``):

* Labour is almost free -- ten hands cost $143/day for ~230 extra actions --
  so the binding constraints are *actions* and *market liquidity*, not land.
* One-time crops are worth harvesting at ``max_yield_day``: it costs the same
  tile-days per unit as an early harvest but far fewer actions per unit.
* Selling is throttled by the engine's own price curve, which we replicate
  exactly, so we never dump a premium good past its collapse point.

v1 deliberately excludes animals and fertilizer; those land in v2.
"""

from __future__ import annotations

import math

TURNS_PER_DAY = 24
EPISODE_STEPS = 720
SHED_CAPACITY = 100
MARKET_I0 = 10000
PRICE_FLOOR = 1

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4,
              "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3,
               "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8,
               "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10,
                   "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12,
              "interval": 0, "max_yield": 6, "ongoing": False},
}

PRODUCTS = [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
]

MARKET_PARAMS = {
    "WHEAT": {"base": 25, "T": 400, "below_func": "sqrt", "below_target": 0.80,
              "above_func": "log", "above_target": 0.20},
    "CARROT": {"base": 35, "T": 450, "below_func": "log", "below_target": 0.20,
               "above_func": "sqrt", "above_target": 0.70},
    "TOMATO": {"base": 60, "T": 200, "below_func": "linear", "below_target": 0.40,
               "above_func": "sqrt", "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "T": 100, "below_func": "sqrt", "below_target": 0.70,
                   "above_func": "linear", "above_target": 1.60},
    "MELON": {"base": 250, "T": 300, "below_func": "log", "below_target": 0.20,
              "above_func": "sq", "above_target": 3.60},
    "EGG": {"base": 50, "T": 332, "below_func": "linear", "below_target": 0.40,
            "above_func": "log", "above_target": 0.20},
    "MILK": {"base": 160, "T": 122, "below_func": "sqrt", "below_target": 0.60,
             "above_func": "linear", "above_target": 1.60},
    "WOOL": {"base": 200, "T": 105, "below_func": "log", "below_target": 0.20,
             "above_func": "sq", "above_target": 3.20},
    "FERTILIZER": {"base": 100, "T": 200, "below_func": "linear", "below_target": 0.40,
                   "above_func": "linear", "above_target": 0.40},
}

LAND_PRICES = [1000, 2000, 4000]
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}

DEFAULTS = {
    # Labour.
    "max_hands": 12,
    "hire_money_frac": 0.06,
    "hire_hours": (0, 1),
    # Land.
    "land_reserve": 600,
    "land_last_day": 22,
    # Market.
    "sell_floor_frac": 0.55,
    "endgame_relax_days": 2.0,
    "seed_buffer": 6,
    "seed_money_frac": 0.35,
    # Planning.
    "plant_cutoff_slack": 1,
    "melon_max_tiles": 24,
    "min_cash": 60,
}


# --------------------------------------------------------------------------
# Market price model (mirrors the engine exactly)
# --------------------------------------------------------------------------

def _shape(func, x):
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    return x


def price_at(item, inventory):
    p = MARKET_PARAMS[item]
    base = p["base"]
    if inventory < MARKET_I0:
        f = p["below_func"]
        amp = p["below_target"] * base / _shape(f, p["T"])
        value = base + amp * _shape(f, MARKET_I0 - inventory)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / _shape(f, p["T"])
        value = base - amp * _shape(f, inventory - MARKET_I0)
    return max(PRICE_FLOOR, int(round(value)))


def sellable_quantity(item, inventory, want, floor_price):
    """Largest q <= want whose marginal price stays at or above ``floor_price``.

    Sales at the $1 floor do not add to market inventory, so once we are at the
    floor the price cannot fall further and holding back buys nothing.
    """
    if want <= 0:
        return 0
    if price_at(item, inventory) <= PRICE_FLOOR:
        return want
    lo, hi = 0, want
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if price_at(item, inventory + mid - 1) >= floor_price:
            lo = mid
        else:
            hi = mid - 1
    return lo


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def shed_tiles(board_size):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def quadrant_of(x, y, board_size):
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(pos, target):
    x, y = pos
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return None


# --------------------------------------------------------------------------
# Crop planning
# --------------------------------------------------------------------------

def water_window(crop):
    cd = CROPS[crop]
    return (cd["max_yield_day"] + 1) // 2, cd["max_yield_day"]


def harvest_age(crop):
    """Age in days at which we take the crop off the tile."""
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["first_yield_day"] + (cd["max_yield"] - 1) * cd["interval"]
    return cd["max_yield_day"]


def crop_rate(crop):
    """Units per tile-day using our standard watering plan (no fertilizer)."""
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["max_yield"] / (harvest_age(crop) + 1)
    start, end = water_window(crop)
    bonus_days = max(0, min(end, cd["max_yield_day"]) - start + 1)
    units = min(cd["max_yield"], 1 + bonus_days)
    return units / max(1, cd["max_yield_day"])


def crop_units(crop):
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["max_yield"]
    start, end = water_window(crop)
    return min(cd["max_yield"], 1 + max(0, end - start + 1))


def crop_score(crop, market_inventory, planted_counts, params):
    """Expected $/tile-day if we plant this crop now.

    The price is evaluated at the market inventory we expect *after* our own
    in-flight production lands, which is what stops the planner from filling
    the whole farm with a crop that collapses on contact.
    """
    cd = CROPS[crop]
    units = crop_units(crop)
    in_flight = planted_counts.get(crop, 0) * units
    inv = market_inventory.get(crop, MARKET_I0) + in_flight + units
    expected = price_at(crop, inv)
    cycle_days = max(1, harvest_age(crop))
    return (units * expected - cd["seed"]) / cycle_days


def plantable(crop, day, last_day, params):
    return day + harvest_age(crop) <= last_day + params["plant_cutoff_slack"]


# --------------------------------------------------------------------------
# Job construction
# --------------------------------------------------------------------------

def build_jobs(obs, farm, private, params, board_size, day, hours_left, endgame):
    """Every worthwhile tile action this turn, valued in dollars."""
    tiles = farm["tiles"]
    market_inventory = obs["market"]["inventory"]
    seeds = private["seeds"]
    jobs = []

    planted_counts = {}
    for row in tiles:
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                planted_counts[tile["crop"]] = planted_counts.get(tile["crop"], 0) + 1

    last_day = EPISODE_STEPS // TURNS_PER_DAY - 1
    choice = None
    if not endgame:
        candidates = [
            (crop_score(c, market_inventory, planted_counts, params), c)
            for c in CROPS
            if plantable(c, day, last_day, params)
            and not (c == "MELON" and planted_counts.get("MELON", 0) >= params["melon_max_tiles"])
        ]
        candidates.sort(reverse=True)
        if candidates and candidates[0][0] > 0:
            choice = candidates[0][1]

    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue

            if tile is None:
                if choice is not None and seeds.get(choice, 0) > 0:
                    score = crop_score(choice, market_inventory, planted_counts, params)
                    jobs.append({
                        "pos": (x, y), "action": ["PLANT", choice],
                        "value": score * harvest_age(choice), "kind": "PLANT",
                        "crop": choice,
                    })
                continue

            kind = tile.get("kind")

            if kind == "WEED":
                jobs.append({
                    "pos": (x, y), "action": ["DIG"], "kind": "DIG",
                    "value": 0.0 if endgame else 30.0,
                })
                continue

            if kind != "PLANT":
                continue

            crop = tile["crop"]
            cd = CROPS[crop]
            age = day - tile["planted_day"]
            units = tile.get("yield_units", 0)
            unit_price = price_at(crop, market_inventory.get(crop, MARKET_I0))

            ripe = units > 0 and age >= cd["first_yield_day"]
            if ripe and (endgame or age >= harvest_age(crop) or units >= cd["max_yield"]):
                jobs.append({
                    "pos": (x, y), "action": ["HARVEST"], "kind": "HARVEST",
                    "value": units * unit_price,
                })
                continue

            if endgame:
                continue

            if tile.get("watered_today"):
                continue

            # A plant that already missed yesterday dies tonight without water.
            must_water = tile.get("consecutive_unwatered", 0) >= 1
            start, end = water_window(crop)
            in_window = (not cd["ongoing"]) and start <= age <= end and units < cd["max_yield"]
            bonus_water = cd["ongoing"] or in_window

            if not (must_water or bonus_water):
                continue

            value = 0.0
            if must_water:
                remaining = max(1, harvest_age(crop) - age)
                value += crop_rate(crop) * remaining * unit_price
            if in_window:
                value += unit_price
            jobs.append({
                "pos": (x, y), "action": ["WATER"], "kind": "WATER",
                "value": value, "urgent": must_water,
            })

    return jobs, choice


# --------------------------------------------------------------------------
# Unit assignment
# --------------------------------------------------------------------------

def assign_units(units, jobs, board_size, hours_left, seeds, endgame, shed_total):
    """Greedy value-per-turn matching between units and tile jobs."""
    pairs = []
    for ui, (pos, _inv) in enumerate(units):
        for ji, job in enumerate(jobs):
            dist = distance(pos, job["pos"])
            if dist > hours_left:
                continue
            pairs.append((job["value"] / (dist + 1.0), -dist, ui, ji))
    pairs.sort(reverse=True)

    taken_unit = {}
    taken_job = set()
    plant_budget = dict(seeds)
    for _score, _negdist, ui, ji in pairs:
        if ui in taken_unit or ji in taken_job:
            continue
        job = jobs[ji]
        if job["kind"] == "PLANT":
            crop = job["crop"]
            if plant_budget.get(crop, 0) <= 0:
                continue
            plant_budget[crop] -= 1
        taken_unit[ui] = ji
        taken_job.add(ji)

    actions = []
    for ui, (pos, inv) in enumerate(units):
        ji = taken_unit.get(ui)
        if ji is None:
            actions.append(idle_action(pos, inv, board_size, endgame, shed_total))
            continue
        job = jobs[ji]
        if tuple(pos) == tuple(job["pos"]):
            actions.append(list(job["action"]))
        else:
            move = step_toward(pos, job["pos"])
            actions.append(move if move else ["PASS"])
    return actions


def idle_action(pos, inv, board_size, endgame, shed_total):
    """Idle units walk their harvest back to the shed rather than stand still."""
    carrying = sum(v for v in inv.values() if v > 0)
    if carrying <= 0:
        return ["PASS"]
    targets = shed_tiles(board_size)
    target = min(targets, key=lambda t: distance(pos, t))
    if tuple(pos) == tuple(target):
        return ["DROP"] if shed_total + carrying <= SHED_CAPACITY or endgame else ["PASS"]
    move = step_toward(pos, target)
    return move if move else ["PASS"]


# --------------------------------------------------------------------------
# Market planning
# --------------------------------------------------------------------------

def plan_market(obs, farm, private, params, board_size, day, hour, step, chosen_crop, endgame):
    orders = []
    money = farm["money"]
    market_inventory = obs["market"]["inventory"]
    shed = private["shed"]
    tiles = farm["tiles"]

    slots = 10

    # --- Hire. Each hand is one order, so hiring eats the whole early budget.
    if hour in params["hire_hours"] and not endgame:
        hours_left = TURNS_PER_DAY - hour - 1
        pending = sum(
            1
            for row in tiles
            for tile in row
            if tile is not None and tile != "LOCKED"
        )
        empty = sum(1 for row in tiles for tile in row if tile is None)
        workload = pending + min(empty, 25)
        needed = max(0, math.ceil(workload * 2.2 / max(1, hours_left)) - 1 - len(farm["hands"]))
        budget = money * params["hire_money_frac"]
        spent = 0.0
        hired = 0
        n = farm["hires_today"]
        while (
            hired < needed
            and len(farm["hands"]) + hired < params["max_hands"]
            and slots > 0
        ):
            cost = _fib(n)
            if spent + cost > budget or money - spent - cost < params["min_cash"]:
                break
            orders.append(["HIRE"])
            spent += cost
            money -= cost
            n += 1
            hired += 1
            slots -= 1

    # --- Land. Twenty-five tiles for $1k/$2k/$4k is cheap while days remain.
    extra = len(farm["unlocked_quadrants"]) - 1
    if (
        slots > 0
        and not endgame
        and extra < len(LAND_PRICES)
        and day <= params["land_last_day"]
    ):
        cost = LAND_PRICES[extra]
        empty = sum(1 for row in tiles for tile in row if tile is None)
        if money - cost >= params["land_reserve"] and empty <= 8:
            orders.append(["BUY_LAND"])
            money -= cost
            slots -= 1

    # --- Seeds for the crop the planner picked.
    if slots > 0 and chosen_crop is not None and not endgame:
        empty = sum(1 for row in tiles for tile in row if tile is None)
        have = private["seeds"].get(chosen_crop, 0)
        want = min(empty, params["seed_buffer"]) - have
        unit_cost = CROPS[chosen_crop]["seed"]
        spendable = max(0, money - params["min_cash"]) * params["seed_money_frac"]
        affordable = int(spendable // unit_cost)
        want = min(want, affordable)
        if want > 0:
            orders.append(["BUY_SEED", chosen_crop, want])
            money -= want * unit_cost
            slots -= 1

    # --- Sell. Throttle each product at its own collapse point, then relax as
    # the season closes so nothing is left unsold.
    days_left = (EPISODE_STEPS - step) / TURNS_PER_DAY
    relax = params["endgame_relax_days"]
    if days_left <= 0.08:
        floor_frac = 0.0
    elif days_left < relax:
        floor_frac = params["sell_floor_frac"] * (days_left / relax)
    else:
        floor_frac = params["sell_floor_frac"]

    shed_total = sum(v for v in shed.values() if v > 0)
    overflow = max(0, shed_total - SHED_CAPACITY + 20)

    stock = [(item, shed.get(item, 0)) for item in PRODUCTS if shed.get(item, 0) > 0]
    stock.sort(key=lambda kv: -price_at(kv[0], market_inventory.get(kv[0], MARKET_I0)) * kv[1])
    for item, have in stock:
        if slots <= 0:
            break
        inv = market_inventory.get(item, MARKET_I0)
        floor_price = max(PRICE_FLOOR, MARKET_PARAMS[item]["base"] * floor_frac)
        quantity = sellable_quantity(item, inv, have, floor_price)
        if quantity < have and overflow > 0:
            forced = min(have - quantity, overflow)
            quantity += forced
            overflow -= forced
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            slots -= 1

    return orders[:10]


def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def _play(obs, params):
    player = obs["player"]
    farm = obs["farms"][player]
    private = obs["private"]
    tiles = farm["tiles"]
    board_size = len(tiles)
    step = obs.get("step", 0)
    day = obs.get("day", step // TURNS_PER_DAY)
    hour = obs.get("hour", step % TURNS_PER_DAY)
    hours_left = TURNS_PER_DAY - hour - 1

    inventories = private.get("inventories", [{}])
    positions = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
    units = []
    for idx, pos in enumerate(positions):
        inv = inventories[idx] if idx < len(inventories) else {}
        units.append((pos, dict(inv)))

    shed_total = sum(v for v in private["shed"].values() if v > 0)
    endgame = step >= EPISODE_STEPS - 2

    jobs, chosen_crop = build_jobs(
        obs, farm, private, params, board_size, day, hours_left, endgame
    )
    unit_actions = assign_units(
        units, jobs, board_size, hours_left, private["seeds"], endgame, shed_total
    )

    if endgame:
        unit_actions = terminal_actions(units, board_size, private["shed"])

    market = plan_market(
        obs, farm, private, params, board_size, day, hour, step, chosen_crop, endgame
    )

    return {
        "farmer": unit_actions[0] if unit_actions else ["PASS"],
        "hands": unit_actions[1:],
        "market": market,
    }


def terminal_actions(units, board_size, shed):
    """On the last actionable step, only cash counts: bank what can be banked."""
    access = set(shed_tiles(board_size))
    room = max(0, SHED_CAPACITY - sum(v for v in shed.values() if v > 0))
    actions = []
    for pos, inv in units:
        carrying = sum(v for k, v in inv.items() if v > 0 and k in PRODUCTS)
        if carrying > 0 and tuple(pos) in access and room > 0:
            actions.append(["DROP"])
            room -= min(room, carrying)
        else:
            actions.append(["PASS"])
    return actions


def make_agent(params=None):
    merged = dict(DEFAULTS)
    if params:
        merged.update(params)

    def agent(obs):
        try:
            return _play(obs, merged)
        except Exception:
            hands = []
            try:
                hands = [["PASS"]] * len(obs["farms"][obs["player"]]["hands"])
            except Exception:
                pass
            return {"farmer": ["PASS"], "hands": hands, "market": []}

    return agent


agent = make_agent()
