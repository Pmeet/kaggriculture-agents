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


def agent(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    private = obs["private"]
    seeds = private["seeds"]
    shed = private["shed"]
    farmer_x, farmer_y = farm["farmer"]
    tile = farm["tiles"][farmer_y][farmer_x]

    if obs["step"] >= 718:
        board_size = len(farm["tiles"])
        half = board_size // 2
        shed_access = {
            (half - 1, half - 1),
            (half, half - 1),
            (half - 1, half),
            (half, half),
        }
        projected_shed = dict(shed)
        inventories = private["inventories"]

        farmer = ["PASS"]
        if (
            inventories[0]
            and (farmer_x, farmer_y) in shed_access
            and tile != "LOCKED"
        ):
            farmer = ["DROP"]
            for item, quantity in inventories[0].items():
                projected_shed[item] = projected_shed.get(item, 0) + quantity

        hands = []
        for index, (hand_x, hand_y) in enumerate(farm["hands"], start=1):
            hand_tile = farm["tiles"][hand_y][hand_x]
            inventory = inventories[index]
            if inventory and (hand_x, hand_y) in shed_access and hand_tile != "LOCKED":
                hands.append(["DROP"])
                for item, quantity in inventory.items():
                    projected_shed[item] = projected_shed.get(item, 0) + quantity
            else:
                hands.append(["PASS"])

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
