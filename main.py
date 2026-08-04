SELLABLE_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)
SHED_CAPACITY = 100


def _terminal_unit_actions(farm, inventories, shed, market_prices):
    board_size = len(farm["tiles"])
    half = board_size // 2
    shed_access = {
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    }
    positions = [farm["farmer"], *farm["hands"]]
    actions = [["PASS"] for _ in positions]
    projected_shed = dict(shed)
    room = max(0, SHED_CAPACITY - sum(projected_shed.values()))
    eligible = []

    for unit_index, (position, inventory) in enumerate(
        zip(positions, inventories, strict=True)
    ):
        unit_x, unit_y = position
        tile = farm["tiles"][unit_y][unit_x]
        positive_inventory = {
            item: quantity
            for item, quantity in inventory.items()
            if quantity > 0
        }
        sellable_inventory = {
            item: quantity
            for item, quantity in positive_inventory.items()
            if item in SELLABLE_PRODUCTS
        }
        if (
            room > 0
            and sellable_inventory
            and (unit_x, unit_y) in shed_access
            and tile != "LOCKED"
        ):
            eligible.append(
                (unit_index, positive_inventory, sellable_inventory)
            )

    total_eligible_inventory = sum(
        sum(positive_inventory.values())
        for _, positive_inventory, _ in eligible
    )
    if total_eligible_inventory <= room:
        for unit_index, positive_inventory, _ in eligible:
            actions[unit_index] = ["DROP"]
            for item, quantity in positive_inventory.items():
                projected_shed[item] = projected_shed.get(item, 0) + quantity
        return actions[0], actions[1:], projected_shed

    states = {0: (0, ())}
    for _, positive_inventory, sellable_inventory in eligible:
        choices = [(["PASS"], {}, 0, 0)]
        inventory_total = sum(positive_inventory.values())
        if inventory_total <= room:
            drop_value = sum(
                max(1, market_prices.get(item, 1)) * quantity
                for item, quantity in sellable_inventory.items()
            )
            choices.append(
                (["DROP"], positive_inventory, inventory_total, drop_value)
            )
        for item in SELLABLE_PRODUCTS:
            available = sellable_inventory.get(item, 0)
            unit_price = max(1, market_prices.get(item, 1))
            for quantity in range(1, min(available, room) + 1):
                action = ["PLACE", item, quantity]
                if len(positive_inventory) == 1 and quantity == available:
                    action = ["DROP"]
                choices.append(
                    (action, {item: quantity}, quantity, unit_price * quantity)
                )

        next_states = {}
        for used, (value, selections) in states.items():
            for choice in choices:
                next_used = used + choice[2]
                if next_used > room:
                    continue
                next_value = value + choice[3]
                existing = next_states.get(next_used)
                if existing is None or next_value > existing[0]:
                    next_states[next_used] = (
                        next_value,
                        (*selections, choice),
                    )
        states = next_states

    _, selections = max(
        states.values(),
        key=lambda state: (state[0], -sum(choice[2] for choice in state[1])),
    )
    for (unit_index, _, _), (action, additions, _, _) in zip(
        eligible,
        selections,
        strict=True,
    ):
        actions[unit_index] = action
        for item, quantity in additions.items():
            projected_shed[item] = projected_shed.get(item, 0) + quantity
    return actions[0], actions[1:], projected_shed


def agent(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    private = obs["private"]
    seeds = private["seeds"]
    shed = private["shed"]
    farmer_x, farmer_y = farm["farmer"]
    tile = farm["tiles"][farmer_y][farmer_x]

    if obs["step"] >= 718:
        inventories = private["inventories"]
        market_prices = obs["market"].get("prices", {})
        farmer, hands, projected_shed = _terminal_unit_actions(
            farm,
            inventories,
            shed,
            market_prices,
        )

        market = [
            ["SELL", item, projected_shed.get(item, 0)]
            for item in SELLABLE_PRODUCTS
            if projected_shed.get(item, 0) > 0
        ]
        return {"farmer": farmer, "hands": hands, "market": market}

    market = []
    carrots_in_shed = shed.get("CARROT", 0)
    if carrots_in_shed > 0:
        market.append(["SELL", "CARROT", carrots_in_shed])
    if seeds.get("CARROT", 0) == 0 and farm["money"] >= 20:
        market.append(["BUY_SEED", "CARROT", 1])

    farmer = ["PASS"]
    if tile is None and seeds.get("CARROT", 0) > 0:
        farmer = ["PLANT", "CARROT"]
    elif (
        isinstance(tile, dict)
        and tile.get("kind") == "PLANT"
        and tile.get("crop") == "CARROT"
    ):
        crop_age = obs.get("day", 0) - tile["planted_day"]
        if crop_age >= 3:
            farmer = ["HARVEST"]
        elif not tile.get("watered_today", False):
            farmer = ["WATER"]

    return {"farmer": farmer, "hands": [], "market": market}
