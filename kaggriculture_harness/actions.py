from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Issue:
    severity: Literal["MALFORMED", "NO_OP", "LOSSY"]
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class _UnitOutcome:
    has_effect: bool
    dropped_units: int = 0
    redundant_fertilizer: bool = False


@dataclass(frozen=True)
class _UnitProjection:
    outcomes: tuple[_UnitOutcome, ...]
    farm: object
    private: object


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
_TURNS_PER_DAY = 24
_SHED_CAPACITY = 100


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


def _engine_executable_market_order(order):
    if not isinstance(order, list) or not order:
        return None
    operation = order[0]
    if operation in {"HIRE", "BUY_LAND"}:
        return [operation]
    if operation not in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}:
        return None
    if len(order) < 3 or not isinstance(order[1], str):
        return None
    try:
        quantity = int(order[2])
    except (TypeError, ValueError, OverflowError):
        return None
    if quantity <= 0:
        return None
    item = order[1]
    if operation == "BUY_SEED" and item in _CROPS:
        return [operation, item, quantity]
    if operation == "BUY_PRODUCT" and item in {"WHEAT", "FERTILIZER"}:
        return [operation, item, quantity]
    if operation == "BUY_ANIMAL" and item in _ANIMALS:
        return [operation, item, quantity]
    if operation == "SELL" and item in _PRODUCTS:
        return [operation, item, quantity]
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


def _prepare_unit_actions(
    obs,
    farmer_action,
    hand_actions,
    blocked_crops,
    *,
    suppress_terminal=False,
):
    player = obs["player"]
    farm = obs["farms"][player]
    entries = [
        ("$.farmer", farm["farmer"], farmer_action),
        *[
            (f"$.hands[{index}]", position, action)
            for index, (position, action) in enumerate(
                zip(farm["hands"], hand_actions, strict=True)
            )
        ],
    ]
    prepared = []
    for path, position, action in entries:
        operation = action[0]
        if operation == "PLANT" and action[1] in blocked_crops:
            prepared.append(["PASS"])
        elif (
            suppress_terminal
            and obs["step"] >= 718
            and operation not in _TERMINAL_ALLOWED_UNIT_OPS
        ):
            prepared.append(["PASS"])
        elif _inspect_unit_action(obs, path, position, action):
            prepared.append(["PASS"])
        else:
            prepared.append(action)
    return prepared


def _dry_run_unit_actions(obs, unit_actions, *, fail_closed_lossy=False):
    player = obs["player"]
    scratch_farm = deepcopy(obs["farms"][player])
    scratch_private = deepcopy(obs["private"])
    if all(action == ["PASS"] for action in unit_actions):
        return _UnitProjection(
            outcomes=tuple(
                _UnitOutcome(has_effect=False) for _ in unit_actions
            ),
            farm=scratch_farm,
            private=scratch_private,
        )

    from kaggle_environments.envs.kaggriculture.kaggriculture import (
        _apply_unit_action,
    )

    board_size = len(scratch_farm["tiles"])
    day = obs.get("day", obs["step"] // _TURNS_PER_DAY)
    effects = []
    for unit_index, action in enumerate(unit_actions):
        position = None
        if unit_index == 0:
            position = scratch_farm["farmer"]
        elif unit_index - 1 < len(scratch_farm["hands"]):
            position = scratch_farm["hands"][unit_index - 1]
        inventory = scratch_private["inventories"][unit_index]
        shed_room = max(
            0,
            _SHED_CAPACITY - sum(scratch_private["shed"].values()),
        )
        inventory_total = sum(
            quantity for quantity in inventory.values() if quantity > 0
        )
        half = board_size // 2
        shed_access_tiles = {
            (half - 1, half - 1),
            (half, half - 1),
            (half - 1, half),
            (half, half),
        }
        tile = None
        if position is not None:
            tile = scratch_farm["tiles"][position[1]][position[0]]
        drop_overflow = 0
        if (
            action[0] == "DROP"
            and position is not None
            and tuple(position) in shed_access_tiles
            and tile != "LOCKED"
        ):
            drop_overflow = max(0, inventory_total - shed_room)
        redundant_fertilizer = (
            action[0] == "FERTILIZE"
            and isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and inventory.get("FERTILIZER", 0) > 0
            and tile.get("fertilized_until_day", -1) >= day + 2
        )
        if fail_closed_lossy and (drop_overflow or redundant_fertilizer):
            effects.append(
                _UnitOutcome(
                    has_effect=False,
                    dropped_units=drop_overflow,
                    redundant_fertilizer=redundant_fertilizer,
                )
            )
            continue
        before_farm = deepcopy(scratch_farm)
        before_private = deepcopy(scratch_private)
        _apply_unit_action(
            scratch_farm,
            scratch_private,
            unit_index,
            action,
            board_size,
            day,
            _TURNS_PER_DAY,
            _SHED_CAPACITY,
        )
        has_effect = (
            scratch_farm != before_farm or scratch_private != before_private
        )
        effects.append(
            _UnitOutcome(
                has_effect=has_effect,
                dropped_units=drop_overflow if has_effect else 0,
                redundant_fertilizer=(
                    redundant_fertilizer if has_effect else False
                ),
            )
        )
    return _UnitProjection(
        outcomes=tuple(effects),
        farm=scratch_farm,
        private=scratch_private,
    )


def _inspect_market_sells(shed, market):
    availability_ranges = {
        item: (max(0, quantity), max(0, quantity))
        for item, quantity in shed.items()
    }
    issues = []
    for index, order in enumerate(market[:10]):
        normalized_order = _normalize_market_order(order)
        is_contract_valid = normalized_order is not None
        projected_order = (
            normalized_order
            if normalized_order is not None
            else _engine_executable_market_order(order)
        )
        if projected_order is None:
            continue
        operation = projected_order[0]
        if operation == "BUY_PRODUCT":
            _, item, quantity = projected_order
            minimum, maximum = availability_ranges.get(item, (0, 0))
            availability_ranges[item] = (minimum, maximum + quantity)
            continue
        if operation != "SELL":
            continue
        _, item, quantity = projected_order
        minimum, maximum = availability_ranges.get(item, (0, 0))
        if maximum == 0 and is_contract_valid:
            issues.append(
                Issue(
                    severity="NO_OP",
                    code="market.sell_empty",
                    path=f"$.market[{index}]",
                    message="SELL has no available post-order shed inventory.",
                )
            )
        availability_ranges[item] = (
            max(0, minimum - quantity),
            max(0, maximum - quantity),
        )
    return issues


def _guard_market_orders(obs, shed, market):
    availability_ranges = {
        item: (max(0, quantity), max(0, quantity))
        for item, quantity in shed.items()
    }
    guarded = []
    for order in market[:10]:
        normalized_order = _normalize_market_order(order)
        if normalized_order is None:
            guarded.append([])
            continue
        operation = normalized_order[0]
        if (
            obs["step"] >= 718
            and operation in _TERMINAL_PURCHASE_OPS
        ):
            guarded.append([])
            continue
        if operation == "SELL":
            _, item, quantity = normalized_order
            minimum, maximum = availability_ranges.get(item, (0, 0))
            if maximum == 0:
                guarded.append([])
                continue
            availability_ranges[item] = (
                max(0, minimum - quantity),
                max(0, maximum - quantity),
            )
        elif operation == "BUY_PRODUCT":
            _, item, quantity = normalized_order
            minimum, maximum = availability_ranges.get(item, (0, 0))
            availability_ranges[item] = (minimum, maximum + quantity)
        guarded.append(normalized_order)
    while guarded and guarded[-1] == []:
        guarded.pop()
    return guarded


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
    normalized_observed_hands = []
    if isinstance(hand_actions, list):
        normalized_observed_hands = [
            _normalize_unit_action(hand_action)
            for hand_action in hand_actions[: len(farm["hands"])]
        ]
    normalized_observed_hands.extend(
        [["PASS"] for _ in range(len(farm["hands"]) - len(normalized_observed_hands))]
    )
    prepared_unit_actions = _prepare_unit_actions(
        obs,
        normalized_farmer_action,
        normalized_observed_hands,
        blocked_crops,
    )
    unit_projection = _dry_run_unit_actions(obs, prepared_unit_actions)
    unit_effects = unit_projection.outcomes
    original_unit_actions = [
        normalized_farmer_action,
        *normalized_observed_hands,
    ]
    unit_paths = [
        "$.farmer",
        *[f"$.hands[{index}]" for index in range(len(farm["hands"]))],
    ]
    for path, original, prepared, outcome in zip(
        unit_paths,
        original_unit_actions,
        prepared_unit_actions,
        unit_effects,
        strict=True,
    ):
        terminal_disallowed = (
            obs["step"] >= 718
            and original[0] not in _TERMINAL_ALLOWED_UNIT_OPS
        )
        if (
            not terminal_disallowed
            and original[0] != "PASS"
            and prepared == original
            and not outcome.has_effect
        ):
            issues.append(
                Issue(
                    severity="NO_OP",
                    code="unit.no_effect",
                    path=path,
                    message=(
                        f"{original[0]} has no effect in sequential unit order."
                    ),
                )
            )
        if outcome.dropped_units:
            issues.append(
                Issue(
                    severity="LOSSY",
                    code="shed.drop_overflow",
                    path=path,
                    message=(
                        f"DROP would destroy {outcome.dropped_units} inventory "
                        "units beyond shed capacity."
                    ),
                )
            )
        if not terminal_disallowed and outcome.redundant_fertilizer:
            issues.append(
                Issue(
                    severity="LOSSY",
                    code="fertilize.redundant",
                    path=path,
                    message=(
                        "FERTILIZE would consume fertilizer without extending "
                        "coverage."
                    ),
                )
            )
    if isinstance(market, list):
        issues.extend(
            _inspect_market_sells(unit_projection.private["shed"], market)
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
    planting_counts = Counter(
        unit_action[1]
        for unit_action in [normalized_farmer, *normalized_hands]
        if unit_action[0] == "PLANT"
    )
    seeds = obs["private"]["seeds"]
    overcommitted_crops = {
        crop for crop, count in planting_counts.items() if count > seeds.get(crop, 0)
    }
    prepared_unit_actions = _prepare_unit_actions(
        obs,
        normalized_farmer,
        normalized_hands,
        overcommitted_crops,
        suppress_terminal=True,
    )
    unit_projection = _dry_run_unit_actions(
        obs,
        prepared_unit_actions,
        fail_closed_lossy=True,
    )
    unit_effects = unit_projection.outcomes
    guarded_unit_actions = [
        prepared
        if prepared[0] == "PASS" or outcome.has_effect
        else ["PASS"]
        for prepared, outcome in zip(
            prepared_unit_actions,
            unit_effects,
            strict=True,
        )
    ]
    normalized_farmer = guarded_unit_actions[0]
    normalized_hands = guarded_unit_actions[1:]
    market = action.get("market")
    if not isinstance(market, list):
        market = []
    normalized_market = _guard_market_orders(
        obs,
        unit_projection.private["shed"],
        market,
    )
    return {
        "farmer": normalized_farmer,
        "hands": normalized_hands,
        "market": normalized_market,
    }
