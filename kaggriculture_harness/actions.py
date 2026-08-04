from collections import Counter
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Issue:
    severity: Literal["MALFORMED", "NO_OP", "LOSSY"]
    code: str
    path: str
    message: str


_CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
_PRODUCTS = _CROPS | {"MILK", "WOOL", "EGG", "FERTILIZER"}
_ANIMALS = {"GOOSE", "COW", "SHEEP"}
_INVENTORY_ITEMS = _CROPS | {
    "MILK",
    "WOOL",
    "EGG",
    "FERTILIZER",
    "GOOSE",
    "COW",
    "SHEEP",
}
_NO_ARGUMENT_UNIT_OPS = {
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "PASS",
    "DROP",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "DIG",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
}
_MOVEMENT_DELTAS = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
_TERMINAL_ALLOWED_UNIT_OPS = {"PASS", "DROP", "PLACE"}
_TERMINAL_PURCHASE_OPS = {
    "BUY_SEED",
    "BUY_PRODUCT",
    "BUY_ANIMAL",
    "HIRE",
    "BUY_LAND",
}


def _is_positive_integer(value):
    return type(value) is int and value > 0


def _is_safe_market_quantity(value):
    return _is_positive_integer(value) and value < 100_000


def _normalize_unit_action(action):
    if not isinstance(action, list) or not action or not isinstance(action[0], str):
        return ["PASS"]

    operation = action[0]
    if operation in _NO_ARGUMENT_UNIT_OPS:
        return action if len(action) == 1 else ["PASS"]
    if operation == "PLANT":
        return (
            action
            if len(action) == 2
            and isinstance(action[1], str)
            and action[1] in _CROPS
            else ["PASS"]
        )
    if operation in {"PICKUP", "PLACE"}:
        if (
            len(action) not in {2, 3}
            or not isinstance(action[1], str)
            or action[1] not in _INVENTORY_ITEMS
        ):
            return ["PASS"]
        if len(action) == 3 and not _is_positive_integer(action[2]):
            return ["PASS"]
        return action
    return ["PASS"]


def _normalize_market_order(order):
    if not isinstance(order, list) or not order or not isinstance(order[0], str):
        return None

    operation = order[0]
    if operation in {"HIRE", "BUY_LAND"}:
        return order if len(order) == 1 else None
    if len(order) != 3 or not _is_safe_market_quantity(order[2]):
        return None
    item = order[1]
    if not isinstance(item, str):
        return None
    if operation == "BUY_SEED" and item in _CROPS:
        return order
    if operation == "BUY_PRODUCT" and item in {"WHEAT", "FERTILIZER"}:
        return order
    if operation == "BUY_ANIMAL" and item in _ANIMALS:
        return order
    if operation == "SELL" and item in _PRODUCTS:
        return order
    return None


def _inspect_unit_action(obs, path, position, action):
    if (
        not isinstance(action, list)
        or not action
        or not isinstance(action[0], str)
    ):
        return []
    operation = action[0]
    if operation not in _MOVEMENT_DELTAS:
        return []

    delta_x, delta_y = _MOVEMENT_DELTAS[operation]
    target_x = position[0] + delta_x
    target_y = position[1] + delta_y
    player = obs["player"]
    tiles = obs["farms"][player]["tiles"]
    if 0 <= target_y < len(tiles) and 0 <= target_x < len(tiles[target_y]):
        return []
    return [
        Issue(
            severity="NO_OP",
            code="unit.out_of_bounds",
            path=path,
            message="Movement would leave the farm and be ignored.",
        )
    ]


def inspect_action(obs, action):
    if not isinstance(action, dict):
        return (
            Issue(
                severity="MALFORMED",
                code="action.not_object",
                path="$",
                message="Action must be an object.",
            ),
        )
    issues = []
    player = obs["player"]
    farm = obs["farms"][player]
    hand_actions = action.get("hands")
    if not isinstance(hand_actions, list):
        issues.append(
            Issue(
                severity="MALFORMED",
                code="hands.not_array",
                path="$.hands",
                message="Hands must be an array of unit actions.",
            )
        )
    elif len(hand_actions) != len(farm["hands"]):
        issues.append(
            Issue(
                severity="MALFORMED",
                code="hands.count_mismatch",
                path="$.hands",
                message="Hand actions must match the observed hand count.",
            )
        )
    farmer_action = action.get("farmer")
    normalized_farmer_action = _normalize_unit_action(farmer_action)
    if normalized_farmer_action == ["PASS"] and farmer_action != ["PASS"]:
        issues.append(
            Issue(
                severity="MALFORMED",
                code="unit.malformed",
                path="$.farmer",
                message="Farmer action has an unknown operation, unsafe value, or arity.",
            )
        )
    market = action.get("market")
    if not isinstance(market, list):
        issues.append(
            Issue(
                severity="MALFORMED",
                code="market.not_array",
                path="$.market",
                message="Market must be an array of orders.",
            )
        )
    elif len(market) > 10:
        issues.append(
            Issue(
                severity="LOSSY",
                code="market.too_many_orders",
                path="$.market",
                message="Only the first ten market orders are processed.",
            )
        )
    if isinstance(market, list):
        for index, order in enumerate(market[:10]):
            if _normalize_market_order(order) is None:
                issues.append(
                    Issue(
                        severity="MALFORMED",
                        code="market.order_malformed",
                        path=f"$.market[{index}]",
                        message="Market order has an unknown operation, unsafe value, or arity.",
                    )
                )
            elif obs["step"] >= 718 and order[0] in _TERMINAL_PURCHASE_OPS:
                issues.append(
                    Issue(
                        severity="LOSSY",
                        code="terminal.purchase",
                        path=f"$.market[{index}]",
                        message="Purchases cannot create cash after the final action.",
                    )
                )
    issues.extend(
        _inspect_unit_action(obs, "$.farmer", farm["farmer"], farmer_action)
    )
    if (
        obs["step"] >= 718
        and normalized_farmer_action[0] not in _TERMINAL_ALLOWED_UNIT_OPS
    ):
        issues.append(
            Issue(
                severity="LOSSY",
                code="terminal.unit_action",
                path="$.farmer",
                message="This unit action cannot create cash after the final action.",
            )
        )
    if isinstance(hand_actions, list):
        for index, (position, hand_action) in enumerate(
            zip(farm["hands"], hand_actions, strict=False)
        ):
            path = f"$.hands[{index}]"
            normalized_hand_action = _normalize_unit_action(hand_action)
            if normalized_hand_action == ["PASS"] and hand_action != ["PASS"]:
                issues.append(
                    Issue(
                        severity="MALFORMED",
                        code="unit.malformed",
                        path=path,
                        message=(
                            "Hand action has an unknown operation, unsafe value, or arity."
                        ),
                    )
                )
            issues.extend(_inspect_unit_action(obs, path, position, hand_action))
            if (
                obs["step"] >= 718
                and normalized_hand_action[0] not in _TERMINAL_ALLOWED_UNIT_OPS
            ):
                issues.append(
                    Issue(
                        severity="LOSSY",
                        code="terminal.unit_action",
                        path=path,
                        message=(
                            "This unit action cannot create cash after the final action."
                        ),
                    )
                )
    plant_requests = []
    if normalized_farmer_action[0] == "PLANT":
        plant_requests.append(("$.farmer", normalized_farmer_action[1]))
    if isinstance(hand_actions, list):
        for index, hand_action in enumerate(hand_actions):
            normalized_hand_action = _normalize_unit_action(hand_action)
            if normalized_hand_action[0] == "PLANT":
                plant_requests.append(
                    (f"$.hands[{index}]", normalized_hand_action[1])
                )
    plant_counts = Counter(crop for _, crop in plant_requests)
    seeds = obs["private"]["seeds"]
    blocked_crops = {
        crop for crop, count in plant_counts.items() if count > seeds.get(crop, 0)
    }
    for path, crop in plant_requests:
        if crop in blocked_crops:
            issues.append(
                Issue(
                    severity="NO_OP",
                    code="plant.overcommitted",
                    path=path,
                    message=(
                        "All requests for this crop will be dropped because seed "
                        "demand exceeds inventory."
                    ),
                )
            )
    return tuple(issues)


def guard_action(obs, action):
    player = obs["player"]
    hand_count = len(obs["farms"][player]["hands"])
    fallback = {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(hand_count)],
        "market": [],
    }
    if not isinstance(action, dict):
        return fallback

    hands = action.get("hands")
    if not isinstance(hands, list):
        hands = []
    normalized_hands = [
        _normalize_unit_action(hand_action)
        for hand_action in hands[:hand_count]
    ]
    normalized_hands.extend(
        [["PASS"] for _ in range(hand_count - len(normalized_hands))]
    )
    normalized_farmer = _normalize_unit_action(action.get("farmer"))
    player = obs["player"]
    farm = obs["farms"][player]
    if _inspect_unit_action(obs, "$.farmer", farm["farmer"], normalized_farmer):
        normalized_farmer = ["PASS"]
    normalized_hands = [
        ["PASS"]
        if _inspect_unit_action(
            obs,
            f"$.hands[{index}]",
            farm["hands"][index],
            hand_action,
        )
        else hand_action
        for index, hand_action in enumerate(normalized_hands)
    ]
    if obs["step"] >= 718:
        if normalized_farmer[0] not in _TERMINAL_ALLOWED_UNIT_OPS:
            normalized_farmer = ["PASS"]
        normalized_hands = [
            hand_action
            if hand_action[0] in _TERMINAL_ALLOWED_UNIT_OPS
            else ["PASS"]
            for hand_action in normalized_hands
        ]
    planting_counts = Counter(
        unit_action[1]
        for unit_action in [normalized_farmer, *normalized_hands]
        if unit_action[0] == "PLANT"
    )
    seeds = obs["private"]["seeds"]
    overcommitted_crops = {
        crop for crop, count in planting_counts.items() if count > seeds.get(crop, 0)
    }
    if normalized_farmer[0] == "PLANT" and normalized_farmer[1] in overcommitted_crops:
        normalized_farmer = ["PASS"]
    normalized_hands = [
        ["PASS"]
        if hand_action[0] == "PLANT" and hand_action[1] in overcommitted_crops
        else hand_action
        for hand_action in normalized_hands
    ]
    market = action.get("market")
    if not isinstance(market, list):
        market = []
    normalized_market = []
    for order in market[:10]:
        normalized_order = _normalize_market_order(order)
        if (
            normalized_order is not None
            and not (
                obs["step"] >= 718
                and normalized_order[0] in _TERMINAL_PURCHASE_OPS
            )
        ):
            normalized_market.append(normalized_order)
    return {
        "farmer": normalized_farmer,
        "hands": normalized_hands,
        "market": normalized_market,
    }
