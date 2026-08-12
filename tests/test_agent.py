"""Contract tests for the submitted agent.

These assert the action contract and the invariants the engine punishes, not a
particular tactic. Strategy is measured empirically in ``lab/`` -- pinning it
here would only make tuning expensive.
"""

import unittest

import main
from main import ANIMALS, CROPS, PRODUCTS, agent

UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PICKUP", "PLACE", "DROP",
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE",
    "FEED", "COLLECT_FERTILIZER", "CARE", "DIG",
}
MARKET_OPS = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}


def observation(
    *,
    money=3000,
    tiles=None,
    seeds=None,
    shed=None,
    day=0,
    step=None,
    inventories=None,
    hand_positions=None,
    market_inventory=None,
    unlocked=("NW",),
    hires_today=0,
):
    board = tiles or [[None for _ in range(10)] for _ in range(10)]
    inventory = market_inventory or {item: 10000 for item in PRODUCTS}
    prices = {item: main.price_at(item, inventory[item]) for item in PRODUCTS}
    return {
        "player": 0,
        "step": day * 24 if step is None else step,
        "day": day,
        "hour": 0 if step is None else step % 24,
        "farms": [
            {
                "money": money,
                "tiles": board,
                "farmer": [4, 4],
                "hands": [list(p) for p in (hand_positions or [])],
                "unlocked_quadrants": list(unlocked),
                "hires_today": hires_today,
            },
            {
                "money": money,
                "tiles": [[None] * 10 for _ in range(10)],
                "farmer": [4, 4],
                "hands": [],
                "unlocked_quadrants": ["NW"],
                "hires_today": 0,
            },
        ],
        "private": {
            "shed": shed or {},
            "seeds": seeds or {},
            "inventories": inventories or [{}],
        },
        "market": {"inventory": inventory, "prices": prices},
        "town": {"unlocked_shops": []},
    }


def locked_board():
    """Only the NW quadrant unlocked, as at the start of a real episode."""
    return [
        [None if x < 5 and y < 5 else "LOCKED" for x in range(10)]
        for y in range(10)
    ]


class ActionContractTest(unittest.TestCase):
    def assert_well_formed(self, action, hands):
        self.assertIsInstance(action, dict)
        self.assertEqual({"farmer", "hands", "market"}, set(action))
        self.assertIsInstance(action["farmer"], list)
        self.assertIn(action["farmer"][0], UNIT_OPS)
        self.assertEqual(hands, len(action["hands"]),
                         "hands list must line up with the hired hands")
        for unit_action in action["hands"]:
            self.assertIsInstance(unit_action, list)
            self.assertIn(unit_action[0], UNIT_OPS)
        self.assertLessEqual(len(action["market"]), 10,
                             "orders past the tenth are silently dropped")
        for order in action["market"]:
            self.assertIsInstance(order, list)
            self.assertIn(order[0], MARKET_OPS)
            if order[0] in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"):
                self.assertEqual(3, len(order))
                self.assertIsInstance(order[2], int)
                self.assertGreater(order[2], 0)

    def test_opening_turn_is_well_formed(self):
        self.assert_well_formed(agent(observation(tiles=locked_board())), 0)

    def test_hands_are_all_given_an_action(self):
        action = agent(observation(
            tiles=locked_board(),
            hand_positions=[(4, 4), (3, 4), (4, 3)],
            inventories=[{}, {}, {}, {}],
        ))
        self.assert_well_formed(action, 3)

    def test_survives_a_full_board_of_every_tile_kind(self):
        board = locked_board()
        board[0][0] = {"kind": "WEED"}
        board[0][1] = {"kind": "COOP"}
        board[0][2] = {"kind": "PASTURE"}
        board[1][0] = {
            "kind": "PLANT", "crop": "MELON", "planted_day": 0,
            "watered_today": False, "consecutive_unwatered": 1,
            "yield_units": 3, "max_lifespan_step": 312, "fertilized_until_day": -1,
        }
        board[1][1] = {
            "kind": "PASTURE", "animal": "COW", "placed_day": 0, "yield_units": 2,
            "fed_today": False, "consecutive_unfed": 1, "cared_today": False,
            "fertilizer_available": True, "pending_care_bonus": 1,
        }
        action = agent(observation(
            tiles=board, day=9, shed={"WHEAT": 20, "MILK": 5, "COW": 1},
            seeds={"MELON": 2}, money=9000,
            hand_positions=[(4, 4)], inventories=[{}, {"WHEAT": 3}],
        ))
        self.assert_well_formed(action, 1)

    def test_reads_an_opponent_farm_that_is_actually_growing_things(self):
        """Every fixture gave the opponent a bare board, so no test ever ran the
        code that reads their production. A live game does from day one."""
        obs = observation(tiles=locked_board(), day=6, money=5000,
                          hand_positions=[(4, 4)], inventories=[{}, {}])
        rival = [[None] * 10 for _ in range(10)]
        rival[0][0] = {
            "kind": "PLANT", "crop": "STRAWBERRY", "planted_day": 0,
            "watered_today": True, "consecutive_unwatered": 0, "yield_units": 1,
            "max_lifespan_step": 400, "fertilized_until_day": -1,
        }
        rival[0][1] = {
            "kind": "PLANT", "crop": "MELON", "planted_day": 1,
            "watered_today": True, "consecutive_unwatered": 0, "yield_units": 0,
            "max_lifespan_step": 400, "fertilized_until_day": -1,
        }
        rival[1][0] = {
            "kind": "PASTURE", "animal": "COW", "placed_day": 0, "yield_units": 2,
            "fed_today": True, "consecutive_unfed": 0, "cared_today": True,
            "fertilizer_available": True, "pending_care_bonus": 2,
        }
        obs["farms"][1]["tiles"] = rival

        supply = main.rival_supply(obs, 0, 6)
        self.assertGreater(supply.get("STRAWBERRY", 0), 0)
        self.assertGreater(supply.get("MILK", 0), 0)

        # The agent must still do real work, not fall back to the PASS handler.
        action = main._play(obs, dict(main.DEFAULTS))
        self.assert_well_formed(action, 1)
        self.assertNotEqual(
            ["PASS"], action["farmer"],
            "a farm with empty tiles and money should never idle the farmer",
        )

    def test_missing_optional_observation_keys_do_not_crash(self):
        obs = observation(tiles=locked_board())
        del obs["day"]
        del obs["hour"]
        self.assert_well_formed(agent(obs), 0)


class SeedCommitmentTest(unittest.TestCase):
    def test_never_requests_more_plants_than_seeds_held(self):
        # The engine drops *every* PLANT for a crop whose demand exceeds stock,
        # so over-committing costs the whole turn's planting, not just one tile.
        action = agent(observation(
            tiles=locked_board(),
            seeds={"CARROT": 2},
            money=0,
            hand_positions=[(4, 4), (3, 4), (4, 3), (3, 3), (2, 2), (1, 1)],
            inventories=[{} for _ in range(7)],
        ))
        units = [action["farmer"], *action["hands"]]
        for crop in CROPS:
            requested = sum(1 for u in units if u[0] == "PLANT" and u[1] == crop)
            self.assertLessEqual(requested, 2, f"over-committed {crop}")


class EndgameTest(unittest.TestCase):
    def test_liquidates_the_shed_on_the_final_actionable_step(self):
        action = agent(observation(
            tiles=locked_board(), step=718, day=29,
            shed={"MELON": 6, "MILK": 4, "WHEAT": 10},
        ))
        sold = {order[1] for order in action["market"] if order[0] == "SELL"}
        self.assertEqual({"MELON", "MILK", "WHEAT"}, sold,
                         "unsold stock scores nothing")

    def test_banks_carried_produce_before_the_whistle(self):
        action = agent(observation(
            tiles=locked_board(), step=718, day=29,
            inventories=[{"MELON": 4}],
        ))
        self.assertEqual(["DROP"], action["farmer"],
                         "produce still in hand at the end is worthless")

    def test_makes_no_investments_once_the_season_cannot_repay_them(self):
        action = agent(observation(
            tiles=locked_board(), step=718, day=29, money=50000,
        ))
        kinds = {order[0] for order in action["market"]}
        self.assertFalse(kinds & {"BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE"})


class CullingTest(unittest.TestCase):
    """Starving an animal is the only way to empty a pen: DIG refuses a tile
    with an animal on it and livestock cannot be sold, but two missed feeds
    delete the animal and leave the structure standing."""

    def pasture_of_sheep(self, count=4):
        board = locked_board()
        for i in range(count):
            board[1][i] = {
                "kind": "PASTURE", "animal": "SHEEP", "placed_day": 0,
                "yield_units": 0, "fed_today": False, "consecutive_unfed": 0,
                "cared_today": False, "fertilizer_available": True,
                "pending_care_bonus": 0,
            }
        return board

    def dead_wool_market(self):
        inventory = {item: main.MARKET_I0 for item in PRODUCTS}
        inventory["WOOL"] = main.MARKET_I0 + 600   # glutted to the $1 floor
        inventory["MILK"] = main.MARKET_I0 - 300   # drained, trading high
        return inventory

    def test_recycles_a_pen_whose_product_has_no_market(self):
        obs = observation(tiles=self.pasture_of_sheep(), day=8, money=6000,
                          market_inventory=self.dead_wool_market())
        obs["town"]["unlocked_shops"] = ["PIZZA_SHOP", "ICE_CREAM_SHOP"]
        params = dict(main.DEFAULTS)
        params["cull_min_edge"] = 800.0
        info = main.census(obs["farms"][0])
        culls = main.cull_candidates(info, params, 8, obs["market"]["inventory"],
                                     main.town_pull(obs, 8, params))
        self.assertTrue(culls, "wool at $1 against milk at $311 should free pens")
        self.assertLessEqual(len(culls), params["cull_max_per_turn"])

    def test_a_culled_animal_is_not_fed(self):
        obs = observation(tiles=self.pasture_of_sheep(), day=8, money=6000,
                          market_inventory=self.dead_wool_market(),
                          shed={"WHEAT": 40})
        obs["town"]["unlocked_shops"] = ["PIZZA_SHOP", "ICE_CREAM_SHOP"]
        params = dict(main.DEFAULTS)
        params["cull_min_edge"] = 800.0
        action = main._play(obs, params)
        units = [action["farmer"], *action["hands"]]
        self.assertEqual(0, sum(1 for u in units if u and u[0] == "FEED"))

    def test_never_culls_when_a_replacement_cannot_mature(self):
        """A pen freed on day 28 has nothing that can reach a first yield."""
        obs = observation(tiles=self.pasture_of_sheep(), day=28, money=6000,
                          market_inventory=self.dead_wool_market())
        params = dict(main.DEFAULTS)
        params["cull_min_edge"] = 800.0
        params["cull_last_day"] = 29
        info = main.census(obs["farms"][0])
        self.assertEqual(set(), main.cull_candidates(
            info, params, 28, obs["market"]["inventory"]))

    def test_off_by_default(self):
        obs = observation(tiles=self.pasture_of_sheep(), day=8, money=6000,
                          market_inventory=self.dead_wool_market())
        info = main.census(obs["farms"][0])
        self.assertEqual(set(), main.cull_candidates(
            info, dict(main.DEFAULTS), 8, obs["market"]["inventory"]))


class MarketModelTest(unittest.TestCase):
    def test_price_model_matches_the_engine(self):
        from kaggle_environments.envs.kaggriculture import kaggriculture as engine

        for item in PRODUCTS:
            for offset in (-4000, -800, -100, 0, 100, 800, 4000):
                self.assertEqual(
                    engine.market_price(item, main.MARKET_I0 + offset),
                    main.price_at(item, main.MARKET_I0 + offset),
                    f"{item} at {offset:+}",
                )

    def test_engine_constants_match(self):
        from kaggle_environments.envs.kaggriculture import kaggriculture as engine

        self.assertEqual(engine.CROPS, CROPS)
        self.assertEqual(engine.ANIMALS, ANIMALS)
        self.assertEqual(engine.PRODUCTS, PRODUCTS)
        self.assertEqual(engine.LAND_PRICES, main.LAND_PRICES)
        self.assertEqual(
            {shop: tuple(products) for shop, products in engine.SHOPS.items()},
            dict(main.SHOP_DEMAND),
        )
        self.assertEqual(engine.MAX_SHOP_INSTANCES, main.MAX_SHOP_INSTANCES)

    def test_shop_unlock_schedule_matches_the_engine(self):
        """The demand prior is only worth anything if the schedule is right."""
        import json
        import os

        from kaggle_environments.envs.kaggriculture import kaggriculture as engine

        spec_path = os.path.join(os.path.dirname(engine.__file__), "kaggriculture.json")
        with open(spec_path) as handle:
            configuration = json.load(handle)["configuration"]
        self.assertEqual(
            main.SHOP_UNLOCK_INTERVAL, configuration["townShopUnlockInterval"]["default"]
        )
        # A shop drains one of each product every four turns, which is the /4.0
        # the projection divides by.
        self.assertEqual(configuration["townShopSellInterval"]["default"], 4)

    def test_future_demand_prior_matches_a_uniform_draw(self):
        """Each unlock is a uniform draw, so a product's share is its shop count."""
        pool = main.SHOP_DEMAND
        for item, share in main.EXPECTED_SHOP_DEMAND.items():
            expected = sum(
                (2 if len(products) == 1 else 1)
                for products in pool.values() if item in products
            ) / len(pool)
            self.assertAlmostEqual(share, expected)
        self.assertNotIn("MELON", main.EXPECTED_SHOP_DEMAND)

    def test_projected_season_demand_tracks_the_sampled_table(self):
        """Sampled over 400 seasons: wheat 523, strawberry 422, melon 30."""
        params = dict(main.DEFAULTS)
        params["town_pull_weight"] = 1.0
        params["future_pull_weight"] = 1.0
        pull = main.town_pull({"town": {"unlocked_shops": []}}, 0, params)
        self.assertAlmostEqual(pull["WHEAT"], 523, delta=60)
        self.assertAlmostEqual(pull["STRAWBERRY"], 422, delta=60)
        self.assertAlmostEqual(pull["MELON"], 30, delta=10)
        self.assertGreater(pull["WHEAT"], pull["STRAWBERRY"])
        self.assertGreater(pull["STRAWBERRY"], pull["MILK"])

    def test_sell_sizing_stops_at_the_price_floor_it_is_given(self):
        quantity = main.sellable_quantity("MELON", main.MARKET_I0, 500, 150.0)
        self.assertGreater(quantity, 0)
        self.assertGreaterEqual(main.price_at("MELON", main.MARKET_I0 + quantity - 1), 150)
        self.assertLess(main.price_at("MELON", main.MARKET_I0 + quantity), 150)


if __name__ == "__main__":
    unittest.main()
