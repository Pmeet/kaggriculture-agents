"""Kaggriculture submission agent: livestock-led economy with economic routing.

What earlier versions taught us, measured on real episodes:

* v1 burned 58% of its unit actions on movement because jobs were scored by
  ``value / (dist + 1)``, so a distant jackpot repeatedly out-bid the tile the
  unit was standing next to. v2 scores jobs as ``value - dist * action_cost``,
  which is the real economics of spending a turn walking, and which makes
  assignments naturally sticky as a unit closes on its target.
* At the end of a v1 game every product except melon traded *above* base --
  the town drains ~3,300 units a season and neither player supplied it. So
  production, not liquidity, is the binding constraint.
* Animals dominate per tile and per action: feed/care/harvest/collect all
  happen on the same tile, so one move amortises over four jobs, and they need
  no watering. Every animal also yields a free fertilizer daily, and fertilizer
  has zero town demand but a $25k glut pot.
* Hiring must be driven by the actual job list. A workload proxy that counted
  tiles under-hired to one hand, which starved the farm of every other action.
  Hands one through eight cost $54 *in total*, so cheap labour is close to free
  and should be taken whenever any work exists.
* Capital must not be spent before it can be worked. Buying livestock on day 0
  left $119 in the bank and no labour, and the animals sat unplaced in the shed
  for twelve days.
"""

from __future__ import annotations

import math

TURNS_PER_DAY = 24
EPISODE_STEPS = 720
LAST_DAY = EPISODE_STEPS // TURNS_PER_DAY - 1
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

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4,
              "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8,
            "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6,
              "interval": 3, "max_held": 6, "product": "WOOL"},
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

# kaggle-environments >= 1.32.4 moved shed operations ahead of the LOCKED
# guard. Set False only if running against an older engine.
SHED_OPS_IGNORE_LOCKED = True

DEFAULTS = {
    # --- Labour. Hands 1..8 cost $54 in total, so cheap labour is nearly free.
    "max_hands": 14,
    "cheap_hire_max": 21,
    "hire_money_frac": 0.32,
    "move_factor": 3.0,
    "jobs_per_plant_day": 1.5,
    "jobs_per_animal_day": 4.0,
    "hire_hours": (0, 1, 2, 3),
    # --- Capital. One budget, spent in payback order; nothing is bought that
    # cannot also be worked, and seeds never eat the reserve.
    "work_reserve": 450,
    "seed_budget_frac": 0.45,
    "expand_when_empty": 14,
    "cash_comfort": 2500.0,
    "discount_rate": 0.02,
    "starved_discount": 0.16,
    "land_last_day": 20,
    "animal_last_day": 22,
    "animal_reserve": 500,
    "max_structures_ahead": 4,
    # Milk and wool trade near $320 and $250 against $160/$200 bases because
    # the town drains them and nobody supplies them. Eggs cap out near $65, and
    # a goose still costs $300 and a daily wheat, so it loses to a cow outright.
    # Herd size is the single biggest driver of income: a ladder replay we lost
    # ran 452 animal-days to our 220.
    "target_cows": 16,
    "target_sheep": 10,
    "target_geese": 0,
    # --- Feed.
    "feed_buffer_days": 2,
    "wheat_buy_max_price": 60,
    "pickup_batch": 8,
    # --- Market.
    "sell_floor_frac": 0.4,
    "max_price_impact": 0.32,
    "endgame_relax_days": 1.6,
    "seed_buffer": 10,
    "min_cash": 30,
    # --- Routing.
    "action_cost_floor": 9.0,
    "action_cost_cap": 70.0,
    "action_cost_scale": 0.5,
    # At 26 this cap never bound: 32 and 40 played byte-identical games, because
    # melon only ever wanted the ~23 tiles of the opening quadrant. It starts
    # doing work at 20, where the three tiles it frees go to strawberry -- worth
    # +$4,283 paired margin on held-out seeds and a clean 1.000/1.000 gauntlet.
    # Do not lower it further: 18 measures -$1,449 and 16 loses every game.
    "melon_max_tiles": 20,
    # "marginal" prices each empty tile against the tiles committed before it,
    # so a crop stops winning tiles once its own supply has crushed the price.
    # "single" is the old behaviour: one crop wins and takes every tile.
    "tile_alloc": "marginal",
    # Tiles held back for a crop that yields inside `early_cash_days`, while the
    # farm is younger than `early_cash_last_day`. Off until measured.
    # The opening is wheat, not melon. Wheat yields on day 2 and sits in five
    # of the eight shops, so it earns across days 2-10 instead of in one lump,
    # and it is what the town actually drains.
    "early_cash_tiles": 20,
    "early_cash_days": 3,
    "early_cash_last_day": 8,
    "land_weight": 0.5,
    "job_weight": 2.2,
    "dig_fraction": 0.25,
    "build_fraction": 0.8,
    "fertilizer_capture": 0.9,
    # A flat charge per follow-up job priced wheat's whole cycle at $8 -- $260
    # of profit less 6 jobs at $42 -- against a $9 cost to walk one tile, so
    # short-cycle crops could never be planted at all. That was invisible while
    # melon carried the economy; it is the binding constraint once it does not.
    "plant_commitment_cost": 8.0,
    "town_pull_weight": 0.5,
    # --- Robustness to the shop draw. The forecast above is right on average
    # and wrong every particular season, and we only ever play this one.
    # `demand_floor` is what a product nobody wants is still worth (melon has no
    # shop demand at all); `max_crop_share` caps any one crop's slice of the
    # farm once `diversify_after` tiles are committed; `rival_supply_weight`
    # charges the opponent's visible production against our expected price.
    # `demand_floor` and `max_crop_share` are OFF (1.0). Both implement "spread
    # the farm so an unlucky shop draw is survivable", and both cost $25-48k a
    # game, for one reason: melon is not a product, it is the capital pump.
    # 19-20 melon tiles land ~$5.6k in a single lump on day 11, which buys the
    # herd in one purchase while livestock still has 18 days to compound it.
    # 16 tiles land $3.8k, which buys one cow, and the farm never catches up --
    # day 20 shows 6 cows and 2 sheep against 10 and 7. Anything that trims
    # melon below ~19 falls off that cliff, whatever its reason for trimming.
    # Kept switched on a parameter so the cliff can be re-tested if the opening
    # ever gets another way to bank a day-11 lump.
    "demand_floor": 1.0,
    "max_crop_share": 1.0,
    "diversify_after": 6,
    # Earliest day melon may be planted. The opening is worth more spent on
    # what the shops actually drain.
    "melon_first_day": 12,
    # Selective starvation. Two missed feeds delete an animal and leave its pen
    # standing, which is the only way to undo a placement. Off until measured.
    "cull_min_edge": 1e9,
    "cull_last_day": 18,
    "cull_max_per_turn": 3,
    # Charging the opponent's visible production against our expected price.
    # Measures neutral locally (0.500, +$657 held out) and cannot measure better
    # there: the local opponent is a copy of us, so "what they planted" is what
    # we planted. It is a real signal only against a ladder that plays
    # differently, which is where it is being tested.
    "rival_supply_weight": 0.10,
    # Buying land just because the bank is full measures -$3,486. Off.
    "expand_when_rich": 1e9,
    "land_before_livestock": False,
    # Weight on demand from shops that have not unlocked yet. 1.0 is "believe
    # the pool average", and it is also what measures best: +$13.4k paired
    # margin on held-out seeds (0.896) against the agent without it. Both
    # halves matter -- 1.5 collapses to -$6.3k, because over-crediting future
    # wheat demand hands it the whole farm and melon monoculture beats that.
    "future_pull_weight": 1.0,
    # Doing a job on the tile a unit is passing over measured neutral-to-negative
    # head to head (0.512/0.456 against 0.525/0.537 without), even though it
    # lifted the bank ~20% against `starter`. Labour is not the binding
    # constraint -- 16-24% of unit turns are already idle -- so saving actions
    # converts to money only where there is unmet demand to spend them on, and
    # against a real opponent there is not. Kept as a switch, off by default.
    "work_in_passing": False,
    "rival_horizon": 3,
    "sells_first": True,
    "sell_order": "impact",
    # FERTILIZE is off. The engine says one fertilizer is worth +2 strawberry
    # (~$500 at real prices), +3 tomato, +2 wheat, +1 carrot and +0 melon, which
    # looks like an easy 7x over selling it. Measured, it costs ~$2.5k a game:
    # 0.263/0.319 against 0.631/0.594 with it off, and gating it to premium
    # crops only recovers little (0.325/0.347). Not the feed logistics -- no
    # animals escape and feed counts are unchanged. The extra units land in
    # markets we already dominate, so the marginal price is far below the table
    # value. Set a finite edge to re-enable and re-measure.
    "fertilize_min_edge": 1e9,
    "max_sell_slots": 7,
    "shed_margin": 45,
    "carry_limit": 8,
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
    """Largest q <= want whose marginal unit still clears ``floor_price``."""
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


def usable_shed_tiles(tiles):
    """Shed-access tiles we can transact on.

    The rebalanced engine resolves PICKUP, DROP and shed-PLACE *before* its
    LOCKED guard, precisely because hands spawn on all four access tiles and
    three of them start locked. Restricting ourselves to unlocked tiles -- which
    the earlier engine required -- now just walks hands to the far corner for
    nothing, so all four are used and the locked ones are kept as a fallback.
    """
    board_size = len(tiles)
    every = shed_tiles(board_size)
    if SHED_OPS_IGNORE_LOCKED:
        return every
    usable = [(x, y) for (x, y) in every if tiles[y][x] != "LOCKED"]
    return usable or [every[0]]


def nearest_shed(pos, depots):
    return min(depots, key=lambda t: distance(pos, t))


# --------------------------------------------------------------------------
# Crop maths
# --------------------------------------------------------------------------

def water_window(crop):
    cd = CROPS[crop]
    return (cd["max_yield_day"] + 1) // 2, cd["max_yield_day"]


def harvest_age(crop):
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["first_yield_day"] + (cd["max_yield"] - 1) * cd["interval"]
    return cd["max_yield_day"]


def crop_units(crop):
    cd = CROPS[crop]
    if cd["ongoing"]:
        return cd["max_yield"]
    start, end = water_window(crop)
    return min(cd["max_yield"], 1 + max(0, end - start + 1))


def realizable(crop, day):
    """Units and occupancy for a tile planted today, allowing a partial cycle.

    A hard "must complete a full cycle" rule left late tiles fallow and, worse,
    banned strawberry outright -- and strawberry is the most valuable thing on
    the board, because the town drains 572 a season and neither player supplies
    them, so it trades near $300 against a $120 base.
    """
    cd = CROPS[crop]
    days_left = LAST_DAY - day
    if days_left < cd["first_yield_day"]:
        return 0, 0
    if cd["ongoing"]:
        productions = 1 + (days_left - cd["first_yield_day"]) // cd["interval"]
        productions = min(productions, cd["max_yield"])
        occupancy = cd["first_yield_day"] + (productions - 1) * cd["interval"]
        return productions, occupancy
    harvest = min(cd["max_yield_day"], days_left)
    start = (cd["max_yield_day"] + 1) // 2
    bonus = max(0, min(harvest, cd["max_yield_day"]) - start + 1)
    return min(cd["max_yield"], 1 + bonus), harvest


def crop_jobs(crop, occupancy):
    """Plant + waterings + harvests for the plan we actually follow.

    Watering outside the bonus window does nothing for yield, so we only water
    to keep the plant alive (never two dry days running) and then every day
    inside the window. Ongoing crops gain nothing from watering at all beyond
    survival, which is why they are so cheap in actions.
    """
    cd = CROPS[crop]
    if cd["ongoing"]:
        waters = 1 + max(0, occupancy - 1) // 2
        productions = 1 + max(0, occupancy - cd["first_yield_day"]) // max(1, cd["interval"])
        return 1 + waters + min(productions, cd["max_yield"])
    start = (cd["max_yield_day"] + 1) // 2
    survival = max(0, (max(0, start - 1) + 1) // 2)
    window = max(0, min(occupancy, cd["max_yield_day"]) - start + 1)
    return 1 + 1 + survival + window + 1


def animal_profit(name, day, market_inventory, owned, params, pull=None,
                  coverage=None):
    """Dollars a fresh animal returns for the rest of the season.

    Fed and cared for daily, ``pending_care_bonus`` banks one per day and is
    paid out on each scheduled production, so a cow yields 1+2 milk every two
    days and a sheep 1+3 wool every three. Placed on day 0 that is roughly 33
    milk -- about $8k at the prices a starved market actually pays -- against a
    $400 animal, which is the best return on the board and the reason buying
    livestock late is so expensive.
    """
    spec = ANIMALS[name]
    productive = LAST_DAY - day - spec["first_yield_day"]
    if productive < 0:
        return -1.0
    interval = max(1, spec["interval"])
    productions = productive // interval + 1
    units = productions * min(spec["max_held"], 1 + spec["interval"])
    product = spec["product"]
    in_flight = owned.get(name, 0) * units - (pull or {}).get(product, 0)
    price = price_at(product, market_inventory.get(product, MARKET_I0) + in_flight + units)
    fert_price = price_at("FERTILIZER", market_inventory.get("FERTILIZER", MARKET_I0))
    days = LAST_DAY - day
    revenue = units * price + days * fert_price * params["fertilizer_capture"]
    feed = days * price_at("WHEAT", market_inventory.get("WHEAT", MARKET_I0) - 1)
    return revenue - spec["cost"] - feed


SHOP_DEMAND = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
TOWN_CENTRE_PRODUCTS = tuple(p for p in PRODUCTS if p != "FERTILIZER")

# The town unlocks one shop every `SHOP_UNLOCK_INTERVAL` days until it holds
# `MAX_SHOP_INSTANCES`, each drawn uniformly *with replacement* from SHOP_DEMAND.
# So the shops a season will contain are unknown but their distribution is not:
# the expected number of drains a product earns from one future unlock is just
# its share of the pool. Wheat sits in five of the eight shops, strawberry four,
# melon none -- which is why measured season demand runs wheat 523, strawberry
# 422, melon 30.
SHOP_UNLOCK_INTERVAL = 3
MAX_SHOP_INSTANCES = 8
EXPECTED_SHOP_DEMAND = {}
for _shop, _products in SHOP_DEMAND.items():
    _multiplier = 2 if len(_products) == 1 else 1
    for _item in _products:
        EXPECTED_SHOP_DEMAND[_item] = (
            EXPECTED_SHOP_DEMAND.get(_item, 0.0) + _multiplier / len(SHOP_DEMAND)
        )


SHOP_COVERAGE = {
    item: share / max(EXPECTED_SHOP_DEMAND.values())
    for item, share in EXPECTED_SHOP_DEMAND.items()
}


def demand_coverage(obs, day, params):
    """How reliably the town will want a product, in [0, 1].

    Expected demand is not the same as dependable demand. Melon is the extreme:
    no shop demands it at all, so its entire season market is the town centre's
    30 units and nothing that happens at an unlock can ever help it. Wheat sits
    in five of the eight shops, so almost any draw wants some.

    Weighting by coverage is what stops the farm betting the season on one
    number being average. It reads the shops that have actually unlocked and
    falls back to the pool share for the ones still to come, so an unlucky draw
    -- four yarn stores and no bakery -- moves the farm off the crop that draw
    left worthless instead of committing to it on the prior.
    """
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    remaining = max(0, MAX_SHOP_INSTANCES - len(shops))
    seen = {}
    for shop in shops:
        products = SHOP_DEMAND.get(shop)
        if not products:
            continue
        multiplier = 2 if len(products) == 1 else 1
        for item in products:
            seen[item] = seen.get(item, 0.0) + multiplier
    total = len(shops) + remaining
    coverage = {}
    for item in PRODUCTS:
        # Observed shops count for what they are; unopened ones for the average.
        expected = seen.get(item, 0.0) + remaining * EXPECTED_SHOP_DEMAND.get(item, 0.0)
        coverage[item] = expected / max(1.0, total)
    best = max(coverage.values()) or 1.0
    floor = params["demand_floor"]
    return {item: floor + (1.0 - floor) * (value / best)
            for item, value in coverage.items()}


def rival_supply(obs, player, day):
    """Units the opponent's visible farm will still deliver this season.

    `rival_incoming` answers "when do we sell"; this answers "what do we grow".
    Both players sell into one inventory, so a quadrant of their strawberry
    depresses our price exactly as our own would, and the tiles carry planting
    dates so the whole remaining schedule is readable. Planting into what they
    have already committed to is how a market paying $285 becomes one paying $40.
    """
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return {}
    supply = {}
    for row in farms[1 - player]["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                cd = CROPS.get(crop)
                if not cd:
                    continue
                age = day - tile.get("planted_day", day)
                if cd["ongoing"]:
                    left = max(0, cd["max_yield"] - tile.get("yield_units", 0))
                    remaining_days = max(0, LAST_DAY - day)
                    left = min(left, 1 + remaining_days // max(1, cd["interval"]))
                else:
                    left = max(0, crop_units(crop) - tile.get("yield_units", 0))
                    if age > harvest_age(crop) + 2:
                        left = 0
                supply[crop] = supply.get(crop, 0) + left
            elif "animal" in tile:
                spec = ANIMALS.get(tile["animal"])
                if not spec:
                    continue
                productive = LAST_DAY - day - max(
                    0, spec["first_yield_day"] - (day - tile.get("placed_day", day))
                )
                if productive < 0:
                    continue
                interval = max(1, spec["interval"])
                units = (productive // interval + 1) * min(
                    spec["max_held"], 1 + spec["interval"]
                )
                product = spec["product"]
                supply[product] = supply.get(product, 0) + units
    return supply


def rival_incoming(obs, player, day, horizon):
    """Units the opponent's visible farm will deliver to market within `horizon` days.

    Their shed is private but their tiles are not, and a tile carries a
    planting date. A block of melon planted on day 0 is therefore a dated
    announcement of a sale on day 10 -- and because both players sell into one
    inventory, whoever reaches that price first gets it. This is a *timing*
    signal, not a volume one: it says when to sell what we already grew, not
    what to grow.
    """
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return {}
    incoming = {}
    for row in farms[1 - player]["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile["crop"]
                cd = CROPS[crop]
                planted = tile.get("planted_day", day)
                held = tile.get("yield_units", 0)
                if cd["ongoing"]:
                    # Fires on a fixed cadence once mature; count the ticks due.
                    first = planted + cd["first_yield_day"]
                    step = max(1, cd["interval"])
                    due = sum(
                        1 for k in range(cd["max_yield"])
                        if day <= first + k * step <= day + horizon
                    )
                    if due:
                        incoming[crop] = incoming.get(crop, 0) + due
                else:
                    ripe = planted + cd["max_yield_day"]
                    if day <= ripe <= day + horizon:
                        incoming[crop] = incoming.get(crop, 0) + max(held, crop_units(crop))
            elif "animal" in tile:
                spec = ANIMALS[tile["animal"]]
                first = tile.get("placed_day", day) + spec["first_yield_day"]
                step = max(1, spec["interval"])
                due = sum(
                    1 for k in range(40)
                    if day <= first + k * step <= day + horizon
                )
                if due:
                    product = spec["product"]
                    per = min(spec["max_held"], 1 + spec["interval"])
                    incoming[product] = incoming.get(product, 0) + due * per
    return incoming


def town_pull(obs, day, params):
    """Units the town will still drain per product before the season ends.

    The rebalanced engine draws shops *with replacement* up to eight instances,
    so a season can contain four pizza shops and no yarn store. Demand for a
    product therefore swings hugely game to game -- wool runs from 30 to 534
    units, carrot from 84 to 570 -- and the shops that unlocked are public. Most
    of the ladder plays a fixed route and cannot use that; reading it lets us
    grow and price against the demand this particular game actually has.

    Every drained unit is a unit we can sell without moving the price, so this
    is subtracted from the supply we charge against our own expected price.
    """
    town = obs.get("town") or {}
    shops = town.get("unlocked_shops") or []
    days_left = max(0, LAST_DAY - day)
    ticks = days_left * TURNS_PER_DAY
    pull = {}
    for shop in shops:
        products = SHOP_DEMAND.get(shop)
        if not products:
            continue
        multiplier = 2 if len(products) == 1 else 1
        for item in products:
            pull[item] = pull.get(item, 0) + multiplier * ticks / 4.0
    for item in TOWN_CENTRE_PRODUCTS:
        pull[item] = pull.get(item, 0) + ticks / 24.0
    weight = params["town_pull_weight"]
    pull = {item: units * weight for item, units in pull.items()}

    # Shops that have not unlocked yet are the larger half of the season's
    # demand, and on day 0 -- when the crop that will fill the farm is chosen --
    # none of them exist yet. Counting only what has already unlocked therefore
    # prices every crop against the demand of the first three days: wheat scored
    # as if the town wanted 29 units when it will drain over 500, and the farm
    # grew none of it. Each future unlock is credited with the pool average,
    # decaying naturally as real shops replace the prior.
    future_weight = params["future_pull_weight"]
    if future_weight > 0:
        for index in range(len(shops), MAX_SHOP_INSTANCES):
            unlock_day = (index + 1) * SHOP_UNLOCK_INTERVAL
            active_days = LAST_DAY - max(day, unlock_day)
            if active_days <= 0:
                continue
            span = active_days * TURNS_PER_DAY / 4.0
            for item, expected in EXPECTED_SHOP_DEMAND.items():
                pull[item] = pull.get(item, 0.0) + expected * span * future_weight
    return pull


def fertilize_gain(crop, tile, day):
    """Extra units one FERTILIZER buys on this tile, replayed off the engine rules.

    FERTILIZE is active for `day`, `day+1` and `day+2`. Inside a one-time crop's
    bonus window a watered day then adds 2 instead of 1; an ongoing crop doubles
    each scheduled production it covers, but only on days the plant is also
    watered. Measured against the engine: strawberry +2 units, tomato +3, wheat
    +2, carrot +1, and melon **zero** -- melon reaches its six-unit cap on
    watering alone, so fertilizing it is discarded outright.
    """
    cd = CROPS[crop]
    if tile.get("fertilized_until_day", -1) >= day:
        return 0
    planted_day = tile.get("planted_day", day)
    held = tile.get("yield_units", 0)
    if cd["ongoing"]:
        first = planted_day + cd["first_yield_day"]
        step = max(1, cd["interval"])
        return sum(
            1 for k in range(cd["max_yield"])
            if day <= first + k * step <= day + 2
        )
    age = day - planted_day
    start = (cd["max_yield_day"] + 1) // 2
    window = max(0, cd["max_yield_day"] - max(age, start) + 1)
    if window <= 0:
        return 0
    plain = min(cd["max_yield"], held + window)
    boosted = min(cd["max_yield"], held + window + min(3, window))
    return max(0, boosted - plain)


def crop_profit(crop, market_inventory, planted, day, pull=None):
    """Dollars a tile returns over one planting, at the price we expect to get."""
    cd = CROPS[crop]
    units, occupancy = realizable(crop, day)
    if units <= 0:
        return -1.0
    in_flight = planted.get(crop, 0) * units - (pull or {}).get(crop, 0)
    expected = price_at(crop, market_inventory.get(crop, MARKET_I0) + in_flight + units)
    return units * expected - cd["seed"]


def crop_value(crop, market_inventory, planted, day, money, params, pull=None,
               coverage=None):
    """Expected profit per unit of the two things we are actually short of.

    Land and labour are both scarce, so a crop is scored against the tile-days
    *and* the actions it consumes. That ranking is what separates melon and
    strawberry (about $100 and $70 per job) from carrot (about $24 per job):
    carrot wins on tile-days alone, which is why an earlier version spammed it.

    Charging our own in-flight production against the price keeps the planner
    from paving the farm with a crop that collapses on contact, and discounting
    by cycle length keeps it from locking every dollar into a ten-day melon
    while the bank is empty.
    """
    cd = CROPS[crop]
    units, occupancy = realizable(crop, day)
    if units <= 0 or occupancy <= 0:
        return -1.0
    in_flight = planted.get(crop, 0) * units - (pull or {}).get(crop, 0)
    expected = price_at(crop, market_inventory.get(crop, MARKET_I0) + in_flight + units)
    profit = units * expected - cd["seed"]
    if profit <= 0:
        return -1.0
    cost = occupancy * params["land_weight"] + crop_jobs(crop, occupancy) * params["job_weight"]
    starved = 1.0 - min(1.0, money / max(1.0, params["cash_comfort"]))
    rate = params["discount_rate"] + params["starved_discount"] * starved
    value = profit / max(1.0, cost) / (1.0 + rate * occupancy)
    # A crop nobody reliably wants is worth less than its average says, because
    # the average is over seasons and we only ever play this one.
    return value * (coverage or {}).get(crop, 1.0)


# --------------------------------------------------------------------------
# Farm census
# --------------------------------------------------------------------------

def census(farm):
    """One pass over the board; every planner below reads this."""
    out = {
        "empty": [], "weeds": [], "plants": [], "animals": [],
        "empty_structures": [], "planted": {}, "animal_counts": {},
        "structure_counts": {},
    }
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            if tile is None:
                out["empty"].append((x, y))
                continue
            kind = tile.get("kind")
            if kind == "WEED":
                out["weeds"].append((x, y))
            elif kind == "PLANT":
                out["plants"].append(((x, y), tile))
                out["planted"][tile["crop"]] = out["planted"].get(tile["crop"], 0) + 1
            elif "animal" in tile:
                out["animals"].append(((x, y), tile))
                name = tile["animal"]
                out["animal_counts"][name] = out["animal_counts"].get(name, 0) + 1
            else:
                out["empty_structures"].append(((x, y), kind))
                out["structure_counts"][kind] = out["structure_counts"].get(kind, 0) + 1
    return out


def animal_targets(params):
    """Livestock wanted, ordered by value per tile."""
    return (
        ("COW", params["target_cows"]),
        ("SHEEP", params["target_sheep"]),
        ("GOOSE", params["target_geese"]),
    )


def animal_order(params, info, market_inventory, day, owned=None, pull=None,
                 coverage=None):
    """Livestock ranked by profit per dollar, dropping anything unprofitable.

    ``owned`` must count animals already bought and waiting in the shed or being
    carried, not just the placed ones. Pricing the next purchase against the
    placed herd alone made every animal look profitable while a dozen identical
    ones sat unplaced, and the rebalanced engine punishes that hard: town centre
    demand fell from every 12 turns on a rising multiplier to a flat every 24,
    so premium prices no longer recover between our own sales.
    """
    counts = info["animal_counts"] if owned is None else owned
    ranked = []
    for name, target in animal_targets(params):
        worth = animal_profit(name, day, market_inventory, counts, params, pull)
        if worth <= 0:
            continue
        # Deliberately *not* weighted by demand coverage. Tilting toward the
        # best-covered product concentrates the herd into it -- 14 cows and 2
        # sheep rather than 7 and 7 -- and milk and wool are both thin markets
        # that floor after 40-60 surplus units. Spreading production across
        # two of them is worth more than picking the better one, and
        # `animal_profit` already prices each additional animal against the
        # supply of its own product. Measured: -$37k a game with the tilt.
        ranked.append((worth / ANIMALS[name]["cost"], name, target))
    ranked.sort(reverse=True)
    return [(name, target) for _score, name, target in ranked]


def cull_candidates(info, params, day, market_inventory, pull=None, coverage=None):
    """Animals worth more to us dead than alive.

    Two consecutive missed feeds and the engine deletes the animal and leaves
    the pasture or coop standing, so a pen is recyclable at the price of two
    days of not feeding. That is the only way to undo a placement: DIG refuses
    a tile with an animal on it, and livestock cannot be sold.

    It is worth doing exactly when the sitting animal's product has died -- a
    season that drew no yarn store leaves wool at the $1 floor while milk trades
    near $290 -- and only while a replacement still has time to reach its first
    yield. The animal already in the pen cost nothing more to keep, so it is
    priced as if it were free, which biases the comparison against culling.
    """
    if params["cull_min_edge"] >= 1e8 or day > params["cull_last_day"]:
        return set()
    culls = set()
    for pos, tile in info["animals"]:
        name = tile["animal"]
        spec = ANIMALS[name]
        # Already paid for, and already past some of its ramp-up.
        keep = animal_profit(name, day, market_inventory, info["animal_counts"],
                             params, pull) + spec["cost"]
        best_gain, best_name = 0.0, None
        for other, other_spec in ANIMALS.items():
            if other_spec["structure"] != spec["structure"] or other == name:
                continue
            # The pen only frees up after two missed feeds.
            if day + 2 + other_spec["first_yield_day"] > LAST_DAY:
                continue
            gain = animal_profit(other, day + 2, market_inventory,
                                 info["animal_counts"], params, pull) - keep
            if gain > best_gain:
                best_gain, best_name = gain, other
        if best_name and best_gain >= params["cull_min_edge"]:
            culls.add(pos)
        if len(culls) >= params["cull_max_per_turn"]:
            break
    return culls


def livestock_plan(params, info, shed, day, money, market_inventory, carried=None,
                   pull=None, coverage=None):
    """Pens to build and animals to buy, kept consistent with each other.

    Two accounting rules earn their keep here. Animals already sitting in the
    shed have been paid for and are earning nothing, so they claim a pen before
    anything else. And they also claim it against *future purchases* -- an
    earlier draft counted an unplaced animal as "have", stopped building pens
    for it, and then kept re-buying into the same empty pen until 26 animals
    (~$9.4k) were stranded in the shed for the rest of the game.
    """
    free = {}
    for _pos, kind in info["empty_structures"]:
        free[kind] = free.get(kind, 0) + 1

    # An animal in a hand's inventory is in transit to its pen: it is neither
    # placed nor in the shed, and forgetting it made the planner buy a
    # replacement for every animal being walked across the farm.
    carried = carried or {}
    waiting = {}
    for name in ANIMALS:
        n = shed.get(name, 0) + carried.get(name, 0)
        if n > 0:
            kind = ANIMALS[name]["structure"]
            waiting[kind] = waiting.get(kind, 0) + n

    pens = []
    spare = {}
    for kind in set(free) | set(waiting):
        have_free = free.get(kind, 0)
        homeless = waiting.get(kind, 0)
        pens.extend([kind] * max(0, homeless - have_free))
        spare[kind] = max(0, have_free - homeless)

    budget = max(0.0, money - params["work_reserve"] - params["animal_reserve"])
    purchases = []
    if day <= params["animal_last_day"]:
        owned_all = {}
        for name in ANIMALS:
            owned_all[name] = (
                info["animal_counts"].get(name, 0)
                + shed.get(name, 0)
                + carried.get(name, 0)
            )
        for name, target in animal_order(params, info, market_inventory, day,
                                         owned_all, pull, coverage):
            spec = ANIMALS[name]
            if day + spec["first_yield_day"] >= LAST_DAY:
                continue
            kind = spec["structure"]
            short = max(0, target - owned_all.get(name, 0))
            if short <= 0:
                continue
            affordable = int(budget // spec["cost"])
            buy = min(short, spare.get(kind, 0), affordable)
            if buy > 0:
                purchases.append((name, buy))
                spare[kind] = spare.get(kind, 0) - buy
                budget -= buy * spec["cost"]
            # Build ahead only for stock the bank can actually cover.
            ahead = min(short - buy, int(budget // spec["cost"]))
            pens.extend([kind] * max(0, ahead))

    return pens[: params["max_structures_ahead"]], purchases


# --------------------------------------------------------------------------
# Job construction
# --------------------------------------------------------------------------

def build_jobs(obs, farm, private, params, depots, day, hours_left, endgame, info,
               money, carried, pull, coverage=None):
    market_inventory = obs["market"]["inventory"]
    seeds = private["seeds"]
    shed = private["shed"]
    days_left = LAST_DAY - day
    jobs = []

    def add(pos, action, value, kind, **extra):
        job = {"pos": pos, "action": action, "value": value, "kind": kind}
        job.update(extra)
        jobs.append(job)

    def marginal_price(item):
        """What the next unit of `item` actually fetches.

        Priced at the market *after* the stock we are already holding unsold,
        so work whose output cannot be sold stops looking valuable. Fertilizer
        makes this vivid: no town building consumes it, so a shed full of it is
        worth far less than the spot price implies, and valuing collection at
        spot had units gathering dung they could never bank.
        """
        held = shed.get(item, 0) + carried.get(item, 0)
        return price_at(item, market_inventory.get(item, MARKET_I0) + held)

    # ---- Livestock: four co-located jobs per tile, no watering, no replanting.
    fert_price = marginal_price("FERTILIZER")
    culls = cull_candidates(info, params, day, market_inventory, pull, coverage)
    for pos, tile in info["animals"]:
        spec = ANIMALS[tile["animal"]]
        product = spec["product"]
        unit_price = marginal_price(product)
        held = tile.get("yield_units", 0)

        if held > 0:
            # Yield caps at max_held, so a full animal is losing production.
            urgency = 1.8 if held >= spec["max_held"] else 1.0
            add(pos, ["HARVEST"], held * unit_price * urgency, "HARVEST")

        if tile.get("fertilizer_available"):
            add(pos, ["COLLECT_FERTILIZER"], fert_price, "COLLECT_FERTILIZER")

        if endgame:
            continue

        if pos in culls:
            # Deliberately withheld: the pen is worth more holding something
            # else, and starving is the only way to empty it. Its produce is
            # still harvested and its fertilizer still collected on the way out.
            continue

        if not tile.get("fed_today"):
            # Two consecutive missed feeds and the animal is gone for good.
            starving = tile.get("consecutive_unfed", 0) >= 1
            if starving:
                value = spec["cost"] + unit_price * max(0, days_left) * 0.5
            else:
                value = unit_price * 0.9
            # A banked CARE bonus is paid out only if the animal is fed on the
            # production day, and is wiped otherwise -- days of caring lost to
            # one missed meal. On such a day the feed is worth the whole bank.
            since = (day + 1) - tile.get("placed_day", day) - spec["first_yield_day"]
            interval = max(1, spec["interval"])
            if since >= 0 and since % interval == 0:
                value += tile.get("pending_care_bonus", 0) * unit_price
            add(pos, ["FEED"], value, "FEED", need="WHEAT")

        if not tile.get("cared_today") and days_left >= 1:
            # CARE banks +1 on the next production, but only on a fed day.
            add(pos, ["CARE"], unit_price * 0.8, "CARE")

    # ---- Empty structures holding stock we already paid for.
    if not endgame:
        for pos, kind in info["empty_structures"]:
            for name, spec in ANIMALS.items():
                if spec["structure"] != kind or shed.get(name, 0) <= 0:
                    continue
                # An unplaced animal is dead capital; realising it beats planting.
                worth = animal_profit(name, day, market_inventory,
                                      info["animal_counts"], params, pull)
                add(pos, ["PLACE", name, 1], max(50.0, worth + spec["cost"]),
                    "PLACE", need=name)
                break

    # ---- Crops.
    for pos, tile in info["plants"]:
        crop = tile["crop"]
        cd = CROPS[crop]
        age = day - tile["planted_day"]
        held = tile.get("yield_units", 0)
        unit_price = marginal_price(crop)
        ripe = held > 0 and age >= cd["first_yield_day"]

        if ripe and (endgame or age >= harvest_age(crop) or held >= cd["max_yield"]):
            add(pos, ["HARVEST"], held * unit_price, "HARVEST")
            continue
        if endgame or tile.get("watered_today"):
            continue

        must_water = tile.get("consecutive_unwatered", 0) >= 1
        start, end = water_window(crop)
        in_window = (not cd["ongoing"]) and start <= age <= end and held < cd["max_yield"]
        # Fertilizer is worth what it grows, against what it would fetch sold.
        # On strawberry that is roughly seven times better than selling it.
        if shed.get("FERTILIZER", 0) > 0 or carried.get("FERTILIZER", 0) > 0:
            gained = fertilize_gain(crop, tile, day)
            if gained > 0:
                worth = gained * unit_price - marginal_price("FERTILIZER")
                if worth > params["fertilize_min_edge"] * marginal_price("FERTILIZER"):
                    add(pos, ["FERTILIZE"], worth, "FERTILIZE", need="FERTILIZER")

        # An ongoing crop only banks the fertilizer bonus on a day it is also
        # watered, so a fertilized plant must be watered on its production days.
        if cd["ongoing"] and tile.get("fertilized_until_day", -1) >= day:
            first = tile.get("planted_day", day) + cd["first_yield_day"]
            step = max(1, cd["interval"])
            if any(first + k * step == day for k in range(cd["max_yield"])):
                in_window = True

        if not (must_water or in_window):
            continue
        value = unit_price if in_window else 0.0
        if must_water:
            # Losing the water tonight loses everything still to come off it.
            if cd["ongoing"]:
                left = max(0, harvest_age(crop) - age)
                pending = min(cd["max_yield"], max(1, left // max(1, cd["interval"])))
            else:
                pending = max(1, crop_units(crop) - held)
            value += pending * unit_price * 0.8
        add(pos, ["WATER"], value, "WATER")

    # ---- Fill empty tiles: livestock pens near the shed, crops further out.
    wanted, by_distance, n_struct = [], [], 0
    if not endgame and info["empty"]:
        wanted, _purchases = livestock_plan(
            params, info, shed, day, money, market_inventory, carried, pull, coverage
        )
        by_distance = sorted(info["empty"], key=lambda p: distance(p, nearest_shed(p, depots)))
        n_struct = min(len(wanted), len(by_distance))

    # One entry per tile that could actually take a crop, each priced against
    # the ones committed before it. The first entry is also what a weeded tile
    # is worth, since digging it out is what makes that planting possible.
    plan = plan_planting(obs, params, info, day, money, pull,
                         max(1, len(by_distance) - n_struct), coverage)
    crop_choice = plan[0][0] if plan else None
    tile_worth = plan[0][1] if plan else 0.0
    crop_score = plan[0][2] if plan else 0.0

    # ---- Weeds squat on tiles we would otherwise be earning from.
    if not endgame:
        for pos in info["weeds"]:
            add(pos, ["DIG"], tile_worth * params["dig_fraction"] + 25.0, "DIG")

    for i, pos in enumerate(by_distance):
        if i < n_struct:
            kind = wanted[i]
            best = max(
                (animal_profit(n, day, market_inventory,
                               info["animal_counts"], params, pull)
                 for n, sp in ANIMALS.items() if sp["structure"] == kind),
                default=0.0,
            )
            add(pos, ["BUILD_COOP" if kind == "COOP" else "BUILD_PASTURE"],
                max(60.0, best * params["build_fraction"]), "BUILD")
            continue
        if i - n_struct >= len(plan):
            break
        crop, worth, _score = plan[i - n_struct]
        if crop and seeds.get(crop, 0) > 0:
            # A PLANT commits the tile to a whole cycle of watering and
            # harvesting, so its value must be net of the actions that cycle
            # will consume. Pricing it at gross cycle profit let one crop
            # action out-bid a cow's feeding, and the herd starved while the
            # farm planted melons.
            units, occupancy = realizable(crop, day)
            follow_up = max(0, crop_jobs(crop, occupancy) - 1)
            add(pos, ["PLANT", crop],
                max(0.0, worth - follow_up * params["plant_commitment_cost"]),
                "PLANT", crop=crop)

    seed_want = {}
    for crop, _worth, _score in plan[:max(0, len(by_distance) - n_struct)]:
        seed_want[crop] = seed_want.get(crop, 0) + 1

    return jobs, crop_choice, crop_score, seed_want


def pick_crop(obs, params, info, day, money, pull=None, coverage=None):
    market_inventory = obs["market"]["inventory"]
    best, best_score = None, 0.0
    for crop in CROPS:
        if crop == "MELON" and info["planted"].get("MELON", 0) >= params["melon_max_tiles"]:
            continue
        score = crop_value(crop, market_inventory, info["planted"], day, money,
                           params, pull, coverage)
        if score > best_score:
            best, best_score = crop, score
    return best, best_score


def plan_planting(obs, params, info, day, money, pull=None, n_tiles=1,
                  coverage=None):
    """Choose a crop for each empty tile, each priced against the ones before it.

    ``pick_crop`` scores crops once and every empty tile gets the winner, so the
    whole farm goes into whichever crop wins the first comparison: 26 melon
    tiles planted on days 1-2, all harvesting together on day 12, into a market
    whose entire season demand for melon is 30 units. Every one of those tiles
    was priced as though it were the only one being planted, so the 26th tile
    was booked at the marginal value of the first.

    Committing them one at a time, each charged against the price the *next*
    one will get, prices the 26th tile at what it will really fetch. A mix then
    falls out of the arithmetic -- melon keeps winning tiles until its marginal
    value drops below wheat's -- rather than being imposed by a cap, and the
    farm has something to sell during the ten days melon spends in the ground.

    Returns ``(crop, tile_profit, score)`` per tile, in the order tiles should
    be filled.
    """
    market_inventory = obs["market"]["inventory"]
    n_tiles = max(0, int(n_tiles))

    if params.get("tile_alloc", "marginal") != "marginal":
        crop, score = pick_crop(obs, params, info, day, money, pull, coverage)
        if crop is None:
            return []
        worth = max(0.0, crop_profit(crop, market_inventory, info["planted"], day, pull))
        return [(crop, worth, score)] * n_tiles

    planted = dict(info["planted"])

    # Melon holds a tile for ten days and pays nothing until day 12, so a farm
    # that plants only melon earns nothing at all through the first third of the
    # season -- $148 in the bank on day 9, and no cash for the livestock that
    # compounds for the remaining twenty. Per-tile-day melon is still worth four
    # times anything else even after its own supply has crushed the price, so it
    # wins every tile on merit and no amount of marginal pricing changes that.
    # Reserving a few tiles for a crop that yields in two days is the only way to
    # price that option value, since it is a property of the schedule rather than
    # of any one tile. Tiles already carrying a fast crop count toward it.
    fast = [c for c in CROPS if CROPS[c]["first_yield_day"] <= params["early_cash_days"]]
    reserve = 0
    if day <= params["early_cash_last_day"] and fast:
        held = sum(planted.get(c, 0) for c in fast)
        reserve = max(0, params["early_cash_tiles"] - held)

    # No crop may take more than its share of the farm. Marginal pricing already
    # backs a crop off as its own supply lands, but it prices the *average*
    # season: it will still commit the whole quadrant to one crop and then find
    # the draw wanted something else. The cap is what makes a bad draw survivable
    # rather than fatal, and it is why the share is set on tiles rather than on
    # money -- tiles are the thing that cannot be reallocated once committed.
    committed = sum(planted.values()) or 0
    share = params["max_crop_share"]

    plan = []
    for _ in range(n_tiles):
        candidates = fast if len(plan) < reserve else CROPS
        total = committed + len(plan) + 1
        best, best_score = None, 0.0
        for crop in candidates:
            if crop == "MELON" and planted.get("MELON", 0) >= params["melon_max_tiles"]:
                continue
            # Melon occupies a tile for ten days and pays into a market of 30
            # units a season. Keeping it out of the opening frees that land for
            # whatever the shops turn out to want; it earns its place later only
            # on tiles nothing else is waiting for.
            if crop == "MELON" and day < params["melon_first_day"]:
                continue
            if share < 1.0 and total > params["diversify_after"]:
                if planted.get(crop, 0) + 1 > share * total:
                    continue
            score = crop_value(crop, market_inventory, planted, day, money, params,
                               pull, coverage)
            if score > best_score:
                best, best_score = crop, score
        if best is None:
            break
        worth = max(0.0, crop_profit(best, market_inventory, planted, day, pull))
        plan.append((best, worth, best_score))
        planted[best] = planted.get(best, 0) + 1
    return plan


# --------------------------------------------------------------------------
# Assignment
# --------------------------------------------------------------------------

def marginal_action_cost(jobs, units, hours_left, params):
    """What a turn spent walking is worth: the job we drop for lack of capacity.

    With more work than actions, an extra step costs the marginal job we no
    longer reach. With spare capacity, walking is nearly free.
    """
    if not jobs:
        return params["action_cost_floor"]
    capacity = int(units * max(1, hours_left) / params["move_factor"])
    values = sorted((j["value"] for j in jobs), reverse=True)
    if capacity >= len(values):
        return params["action_cost_floor"]
    marginal = values[capacity] * params["action_cost_scale"]
    return max(params["action_cost_floor"], min(params["action_cost_cap"], marginal))


def assign_units(units, jobs, depots, hours_left, seeds, params, shed, endgame,
                 shed_total, action_cost, supplies=()):
    """Greedy matching on ``value - distance * action_cost``.

    Pricing a walk at its real opportunity cost keeps units working the tile in
    front of them, and makes assignments stable turn to turn: as a unit closes
    on a target, that target's score rises with it.
    """
    pickup_needs = {}
    for job in jobs:
        item = job.get("need")
        if item:
            pickup_needs[item] = pickup_needs.get(item, 0) + 1

    pairs = []
    for ui, (pos, inv) in enumerate(units):
        for ji, job in enumerate(jobs):
            item = job.get("need")
            if item and inv.get(item, 0) <= 0:
                if shed.get(item, 0) <= 0:
                    continue
                depot = nearest_shed(pos, depots)
                dist = distance(pos, depot) + 1 + distance(depot, job["pos"])
            else:
                dist = distance(pos, job["pos"])
            if dist > hours_left:
                continue
            pairs.append((job["value"] - dist * action_cost, -dist, ui, ji))
    pairs.sort(reverse=True)

    taken_unit = {}
    taken_job = set()
    plant_budget = dict(seeds)
    stock_budget = {item: shed.get(item, 0) for item in pickup_needs}
    for score, _negdist, ui, ji in pairs:
        if ui in taken_unit or ji in taken_job:
            continue
        if score <= 0 and not endgame:
            continue
        job = jobs[ji]
        if job["kind"] == "PLANT":
            # Over-committing a crop makes the engine drop every PLANT for it.
            crop = job["crop"]
            if plant_budget.get(crop, 0) <= 0:
                continue
            plant_budget[crop] -= 1
        item = job.get("need")
        if item and units[ui][1].get(item, 0) <= 0:
            if stock_budget.get(item, 0) <= 0:
                continue
            stock_budget[item] -= 1
        taken_unit[ui] = ji
        taken_job.add(ji)

    # A unit with nothing profitable in range is still better off walking to the
    # nearest work than standing still, so long as it is not carrying a load.
    # PLANT and supply-carrying jobs are excluded here: the engine drops *every*
    # PLANT for a crop whose demand exceeds seed stock, so an unbudgeted filler
    # assignment silently cancelled real plantings elsewhere on the board.
    unclaimed = [
        ji for ji in range(len(jobs))
        if ji not in taken_job and jobs[ji]["kind"] != "PLANT" and not jobs[ji].get("need")
    ]
    for ui, (pos, inv) in enumerate(units):
        if ui in taken_unit or not unclaimed:
            continue
        if any(v > 0 for k, v in inv.items() if k in PRODUCTS and k not in supplies):
            continue
        best = min(unclaimed, key=lambda ji: distance(pos, jobs[ji]["pos"]))
        taken_unit[ui] = best
        taken_job.add(best)
        unclaimed.remove(best)

    # Units draw from one shared pool so a batched PICKUP cannot promise stock a
    # earlier unit already took, which used to leave 66 pickups a game as no-ops.
    pool = {item: shed.get(item, 0) for item in pickup_needs}

    # Work waiting on the tile a unit is *already standing on* costs one turn;
    # walking back for it later costs the round trip. Units cross the animal
    # block on every shed run, and measurement showed them stepping off a tile
    # with fertilizer waiting on 34% of all moves. Doing the job in passing
    # delays the trip by a turn and is worth it whenever the job beats what a
    # turn is worth.
    en_route = {}
    for ji in range(len(jobs)):
        if ji in taken_job:
            continue
        job = jobs[ji]
        if job["kind"] in ("PLANT", "BUILD", "PLACE"):
            continue
        en_route.setdefault(tuple(job["pos"]), []).append(ji)

    actions = []
    # Each DROP this turn eats into the same shed, so the room left has to be
    # tracked across units: checking every unit against the turn's opening
    # total let several drops overflow together and discard produce.
    room = max(0, SHED_CAPACITY - shed_total)
    for ui, (pos, inv) in enumerate(units):
        # A unit that keeps working while loaded is carrying produce it cannot
        # sell: the shed only receives it at nightfall, and anything past the
        # cap is discarded on the spot. Measured at roughly $5.2k a game, mostly
        # melon and milk. Past a threshold, banking the load outranks the next
        # job -- it is the only route those units have to a market at all.
        load = sum(v for k, v in inv.items()
                   if v > 0 and k in PRODUCTS and k not in supplies)
        if load >= params["carry_limit"] and room > 0:
            target = nearest_shed(pos, depots)
            if tuple(pos) == tuple(target):
                room = max(0, room - load)
                actions.append(["DROP"])
                continue
            move = step_toward(pos, target)
            if move:
                actions.append(move)
                continue

        ji = taken_unit.get(ui)
        if ji is None:
            action = idle_action(pos, inv, depots, room, endgame, supplies)
            if action[0] == "DROP":
                room = max(0, room - sum(v for v in inv.values() if v > 0))
            actions.append(action)
            continue
        job = jobs[ji]
        item = job.get("need")
        if item and inv.get(item, 0) <= 0:
            depot = nearest_shed(pos, depots)
            if tuple(pos) == tuple(depot):
                batch = min(params["pickup_batch"], max(1, pickup_needs.get(item, 1)),
                            pool.get(item, 0))
                if batch <= 0:
                    actions.append(idle_action(pos, inv, depots, room, endgame, supplies))
                    continue
                pool[item] = pool.get(item, 0) - batch
                actions.append(["PICKUP", item, batch])
            else:
                move = step_toward(pos, depot)
                actions.append(move if move else ["PASS"])
            continue
        if tuple(pos) == tuple(job["pos"]):
            actions.append(list(job["action"]))
            continue
        detour = None
        if params["work_in_passing"]:
            detour = _work_in_passing(pos, inv, jobs, en_route, taken_job, action_cost)
        if detour is not None:
            actions.append(detour)
            continue
        move = step_toward(pos, job["pos"])
        actions.append(move if move else ["PASS"])
    return actions


def _work_in_passing(pos, inv, jobs, en_route, taken_job, action_cost):
    """Best unclaimed job on the tile this unit is standing on, if it pays."""
    best, best_value = None, action_cost
    for ji in en_route.get(tuple(pos), ()):
        if ji in taken_job:
            continue
        job = jobs[ji]
        item = job.get("need")
        if item and inv.get(item, 0) <= 0:
            continue
        if job["value"] > best_value:
            best, best_value = ji, job["value"]
    if best is None:
        return None
    taken_job.add(best)
    return list(jobs[best]["action"])


def idle_action(pos, inv, depots, room, endgame, supplies=()):
    """Idle hands walk their harvest home instead of standing on a tile.

    Carried *supplies* are not harvest. Returning a feeder's wheat to the shed
    forced a fresh PICKUP for almost every FEED (350 pickups for 358 feeds),
    which is why one batched trip must be allowed to serve many animals.
    """
    carrying = sum(
        v for k, v in inv.items() if v > 0 and k in PRODUCTS and k not in supplies
    )
    if carrying <= 0:
        return ["PASS"]
    target = nearest_shed(pos, depots)
    if tuple(pos) == tuple(target):
        # DROP dumps the whole inventory and silently discards the overflow.
        if endgame or sum(v for v in inv.values() if v > 0) <= room:
            return ["DROP"]
        return ["PASS"]
    move = step_toward(pos, target)
    return move if move else ["PASS"]


# --------------------------------------------------------------------------
# Market
# --------------------------------------------------------------------------

def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def day_workload(info, params):
    """Jobs the farm will generate over a whole day, not just right now.

    Hiring off the instantaneous job list halved the workforce: at hour 0 a
    plant watered yesterday raises no job, yet it will need water, harvest and
    replanting before the day is out. Sizing labour off tiles under management
    is the honest estimate.
    """
    return (
        len(info["plants"]) * params["jobs_per_plant_day"]
        + len(info["animals"]) * params["jobs_per_animal_day"]
        + min(len(info["empty"]), 30)
        + len(info["weeds"])
    )


def plan_hiring(farm, params, hour, hours_left, workload, money, slots, endgame):
    """Hire against the day's workload, and always take the near-free hands."""
    if endgame or hour not in params["hire_hours"] or hours_left <= 3:
        return [], money, slots
    have = 1 + len(farm["hands"])
    needed = math.ceil(workload * params["move_factor"] / max(1, hours_left)) - have
    if needed <= 0:
        return [], money, slots

    orders = []
    budget = money * params["hire_money_frac"]
    spent = 0.0
    hired = 0
    n = farm["hires_today"]
    while hired < needed and have + hired < params["max_hands"] and slots > 0:
        cost = _fib(n)
        cheap = cost <= params["cheap_hire_max"]
        if money - spent - cost < params["min_cash"]:
            break
        if not cheap and spent + cost > budget:
            break
        orders.append(["HIRE"])
        spent += cost
        n += 1
        hired += 1
        slots -= 1
    return orders, money - spent, slots


def plan_market(obs, farm, private, params, shed, day, hour, step, info,
                endgame, seed_want, carried, pull, incoming, coverage=None):
    orders = []
    money = farm["money"]
    market_inventory = obs["market"]["inventory"]
    slots = 10
    hours_left = TURNS_PER_DAY - hour - 1
    n_animals = len(info["animals"])

    hires, money, slots = plan_hiring(
        farm, params, hour, hours_left, day_workload(info, params), money, slots, endgame
    )
    orders.extend(hires)

    # Everything below competes for one budget, spent strictly in payback order.
    # v2's first draft let each buyer read ``money`` independently, so seeds and
    # livestock both spent the same dollars and the bank hit $36 by day 2.
    budget = money - params["min_cash"]

    # ---- Feed first: an unfed animal is a $400 asset two days from escaping.
    # Wheat already picked up by a feeder still counts as ours. Counting only
    # the shed made every batched PICKUP look like a shortfall and re-bought it,
    # which quietly spent ~$97k a game on wheat we already had.
    if slots > 0 and not endgame and n_animals > 0:
        on_hand = shed.get("WHEAT", 0) + carried.get("WHEAT", 0)
        need = n_animals * (1 + params["feed_buffer_days"]) - on_hand
        unit_price = price_at("WHEAT", market_inventory.get("WHEAT", MARKET_I0) - 1)
        if need > 0 and unit_price <= params["wheat_buy_max_price"]:
            want = min(need, int(max(0.0, budget) // max(1, unit_price)))
            if want > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", want])
                budget -= want * unit_price
                slots -= 1

    # ---- Land, when it is allowed to outrank livestock. The farm is fully
    # invested and broke until day 21, so the fourth quadrant is unaffordable
    # while it would still pay and merely legal afterwards. Buying it before the
    # marginal cow is the only way to reach it in time.
    def buy_land(budget, slots):
        extra = len(farm["unlocked_quadrants"]) - 1
        if slots <= 0 or endgame or extra >= len(LAND_PRICES):
            return budget, slots, False
        if day > params["land_last_day"]:
            return budget, slots, False
        cost = LAND_PRICES[extra]
        room = (len(info["empty"]) <= params["expand_when_empty"]
                or budget - cost >= params["expand_when_rich"])
        if budget - cost >= params["work_reserve"] and room:
            orders.append(["BUY_LAND"])
            return budget - cost, slots - 1, True
        return budget, slots, False

    if params["land_before_livestock"]:
        budget, slots, _bought = buy_land(budget, slots)

    # ---- Livestock next. A cared-for cow returns roughly $415 a day against a
    # $400 price, so an animal-day is the most valuable thing a dollar buys and
    # every day it is bought late is a day of production gone. Ladder replays
    # bear this out: the agent that beat us ran ~200 animal-days to our ~60,
    # with fewer crops and no weeding at all.
    if slots > 0 and not endgame:
        _pens, purchases = livestock_plan(
            params, info, shed, day, budget, market_inventory, carried, pull, coverage
        )
        for name, want in purchases:
            if slots <= 0:
                break
            orders.append(["BUY_ANIMAL", name, want])
            budget -= want * ANIMALS[name]["cost"]
            slots -= 1

    # ---- Seed the tiles we already own before buying any more of anything.
    # The tile plan is a mix, so buy for whichever crop it is shortest of and
    # let successive turns fill the rest in. One order a turn keeps the market
    # slots that sells and livestock need, and buying the largest shortfall
    # first means the crop actually blocking a PLANT gets unblocked first.
    if slots > 0 and not endgame and seed_want:
        deficits = []
        for rank, (crop, tiles) in enumerate(seed_want.items()):
            short = min(tiles, params["seed_buffer"]) - private["seeds"].get(crop, 0)
            if short > 0:
                deficits.append((short, -rank, crop))
        if deficits:
            short, _rank, crop = max(deficits)
            unit_cost = CROPS[crop]["seed"]
            want = min(short, int(max(0.0, budget * params["seed_budget_frac"]) // unit_cost))
            if want > 0:
                orders.append(["BUY_SEED", crop, want])
                budget -= want * unit_cost
                slots -= 1

    # ---- Land. Twenty-five tiles for $1k/$2k/$4k pays back within days, but
    # only once the tiles we already hold are full.
    if not params["land_before_livestock"]:
        budget, slots, _bought = buy_land(budget, slots)

    # Market orders resolve by index, and each player's order i is quoted against
    # the same pre-commit inventory as the opponent's order i. A sell at index 0
    # therefore transacts against a smaller inventory -- a better price -- than
    # the opponent's sell further down their queue. Measured directly: 40 melons
    # sold at index 0 fetch $12,817 against $11,530 at index 5, an 11% swing on
    # queue position alone.
    #
    # Nothing we buy loses by moving later. HIRE and BUY_LAND are atomic, and
    # BUY_SEED and BUY_ANIMAL are fixed-price, so their index is irrelevant;
    # BUY_PRODUCT is quoted at post-buy inventory, which if anything prefers a
    # later slot. So sells go first, capped so purchases keep a few slots.
    sells = plan_sales(market_inventory, shed, params, step, n_animals,
                       params["max_sell_slots"], carried, incoming)
    if params["sells_first"]:
        return (sells + orders)[:10]
    return (orders + sells)[:10]


def plan_sales(market_inventory, shed, params, step, n_animals, slots, carried=None,
               incoming=None):
    """Throttle each product at its own collapse point and cap price impact.

    Town demand drains the market all season, so holding a premium good back is
    not idle capital -- it is waiting for the price to climb back.
    """
    incoming = incoming or {}
    days_left = (EPISODE_STEPS - step) / TURNS_PER_DAY
    relax = params["endgame_relax_days"]
    liquidate = days_left <= params["endgame_relax_days"]
    if days_left <= 0.1:
        floor_frac, impact = 0.0, 1.0
    elif days_left < relax:
        ratio = days_left / relax
        floor_frac = params["sell_floor_frac"] * ratio
        impact = params["max_price_impact"] + (1.0 - params["max_price_impact"]) * (1 - ratio)
    else:
        floor_frac, impact = params["sell_floor_frac"], params["max_price_impact"]

    shed_total = sum(v for v in shed.values() if v > 0)
    # Everything a unit is carrying drops into the shed at end of day, and
    # anything past the cap is discarded outright. Reacting only to the shed's
    # own level ignored that incoming load and quietly threw away about $5.5k a
    # game -- melons and milk, the two things worth most per unit.
    incoming_load = sum(v for v in (carried or {}).values() if v > 0)
    overflow = max(0, shed_total + incoming_load - SHED_CAPACITY + params["shed_margin"])
    # Never sell the wheat tonight's feeding depends on.
    wheat_reserve = 0 if days_left <= 0.1 else max(
        0, n_animals * (1 + params["feed_buffer_days"]) - (carried or {}).get("WHEAT", 0)
    )

    stock = []
    for item in PRODUCTS:
        have = shed.get(item, 0)
        if item == "WHEAT":
            have -= wheat_reserve
        if have > 0:
            inv = market_inventory.get(item, MARKET_I0)
            stock.append((price_at(item, inv) * have, item, have, inv))
    # Queue position is worth about 11% on a premium sale, so the first slot
    # should go to whichever sale loses the most by waiting -- the product whose
    # price falls fastest as its own units land, not simply the biggest pile.
    if params["sell_order"] == "impact":
        ranked = []
        for weight, item, have, inv in stock:
            now = price_at(item, inv)
            after = price_at(item, inv + max(1, have))
            ranked.append(((now - after) * have, weight, item, have, inv))
        ranked.sort(reverse=True)
        stock = [(w, item, have, inv) for _drop, w, item, have, inv in ranked]
    else:
        stock.sort(reverse=True)

    orders = []
    for _weight, item, have, inv in stock:
        if slots <= 0:
            break
        current = price_at(item, inv)
        floor_price = max(PRICE_FLOOR, MARKET_PARAMS[item]["base"] * floor_frac,
                          current * (1.0 - impact))
        # A harvest the opponent has already committed to is a price we will not
        # see again. When their tiles say a block of this product lands within a
        # few days, take the price that exists now rather than the one after
        # their supply arrives.
        soon = incoming.get(item, 0)
        if soon > 0 and not liquidate:
            after = price_at(item, inv + int(soon))
            if after < current:
                floor_price = min(floor_price, max(float(PRICE_FLOOR), float(after)))
        quantity = sellable_quantity(item, inv, have, floor_price)
        if quantity < have and overflow > 0:
            forced = min(have - quantity, overflow)
            quantity += forced
            overflow -= forced
        if quantity > 0:
            orders.append(["SELL", item, quantity])
            slots -= 1
    return orders


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def terminal_actions(units, depots, shed):
    """On the last actionable step only banked cash counts."""
    access = set(depots)
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


def _play(obs, params):
    player = obs["player"]
    farm = obs["farms"][player]
    private = obs["private"]
    step = obs.get("step", 0)
    day = obs.get("day", step // TURNS_PER_DAY)
    hour = obs.get("hour", step % TURNS_PER_DAY)
    hours_left = TURNS_PER_DAY - hour - 1
    endgame = step >= EPISODE_STEPS - 2

    inventories = private.get("inventories", [{}])
    positions = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
    units = []
    for idx, pos in enumerate(positions):
        inv = inventories[idx] if idx < len(inventories) else {}
        units.append((pos, dict(inv)))

    depots = usable_shed_tiles(farm["tiles"])
    carried = {}
    for _pos, inv in units:
        for item, count in inv.items():
            if count > 0:
                carried[item] = carried.get(item, 0) + count
    shed = dict(private["shed"])
    shed_total = sum(v for v in shed.values() if v > 0)
    info = census(farm)
    pull = town_pull(obs, day, params)
    coverage = demand_coverage(obs, day, params)
    # The opponent's committed production competes for exactly the demand we
    # are pricing against, so it is negative town pull.
    if params["rival_supply_weight"] > 0:
        for item, rival_units in rival_supply(obs, player, day).items():
            pull[item] = pull.get(item, 0.0) - rival_units * params["rival_supply_weight"]
    incoming = rival_incoming(obs, player, day, params["rival_horizon"])

    jobs, _crop_choice, _crop_score, seed_want = build_jobs(
        obs, farm, private, params, depots, day, hours_left, endgame, info,
        farm["money"], carried, pull, coverage,
    )

    if endgame:
        unit_actions = terminal_actions(units, depots, shed)
    else:
        action_cost = marginal_action_cost(jobs, len(units), hours_left, params)
        # Wheat in a feeder's hands is stock in transit, not produce to bank.
        supplies = ("WHEAT",) if info["animals"] else ()
        unit_actions = assign_units(
            units, jobs, depots, hours_left, private["seeds"], params,
            shed, endgame, shed_total, action_cost, supplies,
        )

    # The unit phase runs before the market phase, so anything a hand is about
    # to PICKUP has already left the shed by the time our sell orders execute.
    for unit_action in unit_actions:
        if unit_action and unit_action[0] == "PICKUP" and len(unit_action) >= 3:
            item = unit_action[1]
            taken = min(int(unit_action[2]), shed.get(item, 0))
            shed[item] = shed.get(item, 0) - taken
            carried[item] = carried.get(item, 0) + taken

    # ...and a DROP lands *into* the shed before the same turn's sell orders
    # execute. On the last actionable step that is the difference between
    # banking the final harvest and leaving it in the shed scoring nothing.
    if endgame:
        room = max(0, SHED_CAPACITY - sum(v for v in shed.values() if v > 0))
        for unit_action, (_pos, inv) in zip(unit_actions, units):
            if not unit_action or unit_action[0] != "DROP" or room <= 0:
                continue
            for item, count in inv.items():
                if count <= 0:
                    continue
                moved = min(count, room)
                shed[item] = shed.get(item, 0) + moved
                room -= moved

    market = plan_market(
        obs, farm, private, params, shed, day, hour, step, info, endgame,
        seed_want, carried, pull, incoming, coverage,
    )
    return {
        "farmer": unit_actions[0] if unit_actions else ["PASS"],
        "hands": unit_actions[1:],
        "market": market,
    }


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
