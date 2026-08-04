import unittest

from main import agent


def observation(
    *,
    money=3000,
    tile=None,
    seeds=None,
    shed=None,
    day=0,
    step=None,
    inventories=None,
):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[4][4] = tile
    return {
        "player": 0,
        "step": day * 24 if step is None else step,
        "day": day,
        "hour": 0,
        "farms": [
            {
                "money": money,
                "tiles": tiles,
                "farmer": [4, 4],
                "hands": [],
                "unlocked_quadrants": ["NW"],
                "hires_today": 0,
            },
            {},
        ],
        "private": {
            "shed": shed or {},
            "seeds": seeds or {},
            "inventories": inventories or [{}],
        },
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": []},
    }


class AgentStrategyTest(unittest.TestCase):
    def test_buys_one_carrot_seed_when_none_are_available(self):
        action = agent(observation(seeds={"CARROT": 0}))

        self.assertIn(["BUY_SEED", "CARROT", 1], action["market"])

    def test_plants_carrot_on_an_empty_tile_when_a_seed_is_available(self):
        action = agent(observation(seeds={"CARROT": 1}))

        self.assertEqual(["PLANT", "CARROT"], action["farmer"])

    def test_waters_a_young_unwatered_carrot(self):
        carrot = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "watered_today": False,
        }

        action = agent(observation(tile=carrot, seeds={"CARROT": 1}, day=1))

        self.assertEqual(["WATER"], action["farmer"])

    def test_harvests_a_carrot_at_its_max_yield_day(self):
        carrot = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "watered_today": False,
        }

        action = agent(observation(tile=carrot, seeds={"CARROT": 1}, day=3))

        self.assertEqual(["HARVEST"], action["farmer"])

    def test_sells_all_carrots_stored_in_the_shed(self):
        action = agent(
            observation(seeds={"CARROT": 1}, shed={"CARROT": 4})
        )

        self.assertIn(["SELL", "CARROT", 4], action["market"])

    def test_step_718_drops_and_sells_all_recoverable_products(self):
        action = agent(
            observation(
                step=718,
                day=29,
                seeds={"CARROT": 0},
                shed={"CARROT": 4, "MILK": 2},
                inventories=[{"CARROT": 3}],
            )
        )

        self.assertEqual(action["farmer"], ["DROP"])
        self.assertCountEqual(
            action["market"],
            [["SELL", "CARROT", 7], ["SELL", "MILK", 2]],
        )


if __name__ == "__main__":
    unittest.main()
