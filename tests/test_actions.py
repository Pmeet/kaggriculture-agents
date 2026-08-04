import copy
import unittest

from kaggriculture_harness.actions import guard_action, inspect_action


def observation(
    *,
    hand_count=0,
    hand_positions=None,
    seeds=None,
    farmer=(4, 4),
    step=0,
):
    hands = (
        [list(position) for position in hand_positions]
        if hand_positions is not None
        else [[4, 4] for _ in range(hand_count)]
    )
    return {
        "player": 0,
        "step": step,
        "day": 0,
        "hour": 0,
        "farms": [
            {
                "money": 3000,
                "tiles": [[None for _ in range(10)] for _ in range(10)],
                "farmer": list(farmer),
                "hands": hands,
                "unlocked_quadrants": ["NW"],
                "hires_today": 0,
            },
            {},
        ],
        "private": {
            "shed": {},
            "seeds": seeds or {},
            "inventories": [{} for _ in range(len(hands) + 1)],
        },
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": []},
    }


class ActionGuardTest(unittest.TestCase):
    def test_returns_fail_closed_shape_for_a_malformed_action(self):
        guarded = guard_action(observation(hand_count=2), None)

        self.assertEqual(
            guarded,
            {
                "farmer": ["PASS"],
                "hands": [["PASS"], ["PASS"]],
                "market": [],
            },
        )

    def test_reports_a_structured_issue_for_a_malformed_action(self):
        issues = inspect_action(observation(), None)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "MALFORMED")
        self.assertEqual(issues[0].code, "action.not_object")
        self.assertEqual(issues[0].path, "$")

    def test_reports_market_orders_that_the_engine_would_drop(self):
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "CARROT", 1] for _ in range(11)],
        }

        issues = inspect_action(observation(), action)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "LOSSY")
        self.assertEqual(issues[0].code, "market.too_many_orders")
        self.assertEqual(issues[0].path, "$.market")

    def test_reports_a_missing_or_non_list_market(self):
        for market in (None, "bad"):
            with self.subTest(market=market):
                action = {"farmer": ["PASS"], "hands": []}
                if market is not None:
                    action["market"] = market

                issues = inspect_action(observation(), action)

                self.assertEqual(len(issues), 1)
                self.assertEqual(issues[0].code, "market.not_array")
                self.assertEqual(issues[0].path, "$.market")

    def test_reports_an_out_of_bounds_move_as_a_no_op(self):
        action = {"farmer": ["WEST"], "hands": [], "market": []}

        issues = inspect_action(observation(farmer=(0, 0)), action)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "NO_OP")
        self.assertEqual(issues[0].code, "unit.out_of_bounds")
        self.assertEqual(issues[0].path, "$.farmer")

    def test_reports_malformed_unit_and_market_entries(self):
        action = {
            "farmer": ["PLANT", []],
            "hands": [],
            "market": [["SELL", "CARROT", True]],
        }

        issues = inspect_action(observation(), action)

        self.assertEqual(
            {(issue.code, issue.path) for issue in issues},
            {
                ("unit.malformed", "$.farmer"),
                ("market.order_malformed", "$.market[0]"),
            },
        )

    def test_reports_a_hand_count_that_does_not_match_the_observation(self):
        action = {
            "farmer": ["PASS"],
            "hands": [["PASS"]],
            "market": [],
        }

        issues = inspect_action(observation(hand_count=2), action)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "MALFORMED")
        self.assertEqual(issues[0].code, "hands.count_mismatch")
        self.assertEqual(issues[0].path, "$.hands")

    def test_reports_a_malformed_hand_action_at_its_index(self):
        action = {
            "farmer": ["PASS"],
            "hands": [["NORTH", "extra"]],
            "market": [],
        }

        issues = inspect_action(observation(hand_count=1), action)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "unit.malformed")
        self.assertEqual(issues[0].path, "$.hands[0]")

    def test_reports_actions_that_cannot_create_terminal_cash(self):
        action = {
            "farmer": ["PLANT", "CARROT"],
            "hands": [],
            "market": [["BUY_SEED", "CARROT", 1]],
        }

        issues = inspect_action(observation(seeds={"CARROT": 1}, step=718), action)

        self.assertEqual(
            {(issue.code, issue.path) for issue in issues},
            {
                ("terminal.unit_action", "$.farmer"),
                ("terminal.purchase", "$.market[0]"),
            },
        )

    def test_guard_removes_actions_that_cannot_create_terminal_cash(self):
        guarded = guard_action(
            observation(seeds={"CARROT": 1}, step=718),
            {
                "farmer": ["PLANT", "CARROT"],
                "hands": [],
                "market": [["BUY_SEED", "CARROT", 1]],
            },
        )

        self.assertEqual(guarded["farmer"], ["PASS"])
        self.assertEqual(guarded["market"], [])

    def test_reports_a_terminal_hand_action_at_its_index(self):
        issues = inspect_action(
            observation(hand_count=1, step=718),
            {
                "farmer": ["PASS"],
                "hands": [["HARVEST"]],
                "market": [],
            },
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "terminal.unit_action")
        self.assertEqual(issues[0].path, "$.hands[0]")

    def test_inspection_never_hashes_an_untrusted_operation(self):
        issues = inspect_action(
            observation(step=718),
            {"farmer": [[]], "hands": [], "market": []},
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "unit.malformed")

    def test_guard_replaces_an_out_of_bounds_move_with_pass(self):
        guarded = guard_action(
            observation(farmer=(0, 0)),
            {"farmer": ["WEST"], "hands": [], "market": []},
        )

        self.assertEqual(guarded["farmer"], ["PASS"])

    def test_guard_replaces_an_out_of_bounds_hand_move_with_pass(self):
        guarded = guard_action(
            observation(hand_positions=[(0, 0)]),
            {
                "farmer": ["PASS"],
                "hands": [["WEST"]],
                "market": [],
            },
        )

        self.assertEqual(guarded["hands"], [["PASS"]])

    def test_normalizes_hand_actions_to_the_observed_hand_count(self):
        guarded = guard_action(
            observation(hand_count=2),
            {
                "farmer": ["PASS"],
                "hands": [["WEST"]],
                "market": [],
            },
        )

        self.assertEqual(guarded["hands"], [["WEST"], ["PASS"]])

    def test_replaces_malformed_unit_actions_with_pass(self):
        guarded = guard_action(
            observation(hand_count=2),
            {
                "farmer": "PASS",
                "hands": [["NORTH", "extra"], ["PLANT", "UNKNOWN"]],
                "market": [],
            },
        )

        self.assertEqual(guarded["farmer"], ["PASS"])
        self.assertEqual(guarded["hands"], [["PASS"], ["PASS"]])

    def test_rejects_unhashable_values_and_boolean_quantities(self):
        guarded = guard_action(
            observation(hand_count=1),
            {
                "farmer": ["PLANT", []],
                "hands": [["PICKUP", "CARROT", True]],
                "market": [],
            },
        )

        self.assertEqual(guarded["farmer"], ["PASS"])
        self.assertEqual(guarded["hands"], [["PASS"]])

    def test_validates_only_the_first_ten_market_slots(self):
        first_nine = [["SELL", "CARROT", 1] for _ in range(9)]
        guarded = guard_action(
            observation(),
            {
                "farmer": ["PASS"],
                "hands": [],
                "market": [
                    *first_nine,
                    ["SELL", "CARROT", True],
                    ["SELL", "MELON", 1],
                ],
            },
        )

        self.assertEqual(guarded["market"], first_nine)

    def test_rejects_market_quantities_that_hit_the_engine_loop_guard(self):
        guarded = guard_action(
            observation(),
            {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["SELL", "CARROT", 100_000]],
            },
        )

        self.assertEqual(guarded["market"], [])

    def test_fails_all_overcommitted_plant_requests_closed(self):
        guarded = guard_action(
            observation(hand_count=1, seeds={"CARROT": 1}),
            {
                "farmer": ["PLANT", "CARROT"],
                "hands": [["PLANT", "CARROT"]],
                "market": [],
            },
        )

        self.assertEqual(guarded["farmer"], ["PASS"])
        self.assertEqual(guarded["hands"], [["PASS"]])

    def test_reports_every_atomic_plant_request_that_will_be_dropped(self):
        issues = inspect_action(
            observation(hand_count=1, seeds={"CARROT": 1}),
            {
                "farmer": ["PLANT", "CARROT"],
                "hands": [["PLANT", "CARROT"]],
                "market": [],
            },
        )

        self.assertEqual(
            {(issue.code, issue.path) for issue in issues},
            {
                ("plant.overcommitted", "$.farmer"),
                ("plant.overcommitted", "$.hands[0]"),
            },
        )
        self.assertTrue(all(issue.severity == "NO_OP" for issue in issues))

    def test_reports_a_later_unit_action_that_sequentially_becomes_a_no_op(self):
        obs = observation(farmer=(2, 2), hand_positions=[(2, 2)])
        action = {
            "farmer": ["BUILD_COOP"],
            "hands": [["BUILD_PASTURE"]],
            "market": [],
        }

        issues = inspect_action(obs, action)

        self.assertEqual(
            [(issue.code, issue.path) for issue in issues],
            [("unit.no_effect", "$.hands[0]")],
        )

    def test_guard_removes_a_later_unit_action_that_has_no_effect(self):
        guarded = guard_action(
            observation(farmer=(2, 2), hand_positions=[(2, 2)]),
            {
                "farmer": ["BUILD_COOP"],
                "hands": [["BUILD_PASTURE"]],
                "market": [],
            },
        )

        self.assertEqual(guarded["farmer"], ["BUILD_COOP"])
        self.assertEqual(guarded["hands"], [["PASS"]])

    def test_preserves_a_later_action_enabled_by_an_earlier_unit(self):
        obs = observation(
            farmer=(2, 2),
            hand_positions=[(2, 2)],
            seeds={"CARROT": 1},
        )
        obs["farms"][0]["tiles"][2][2] = {"kind": "WEED"}
        action = {
            "farmer": ["DIG"],
            "hands": [["PLANT", "CARROT"]],
            "market": [],
        }

        self.assertEqual(inspect_action(obs, action), ())
        self.assertEqual(guard_action(obs, action), action)

    def test_shared_shed_is_consumed_in_farmer_then_hands_order(self):
        obs = observation(farmer=(4, 4), hand_positions=[(4, 4)])
        obs["private"]["shed"] = {"CARROT": 1}
        action = {
            "farmer": ["PICKUP", "CARROT", 1],
            "hands": [["PICKUP", "CARROT", 1]],
            "market": [],
        }

        issues = inspect_action(obs, action)
        guarded = guard_action(obs, action)

        self.assertEqual(
            [(issue.code, issue.path) for issue in issues],
            [("unit.no_effect", "$.hands[0]")],
        )
        self.assertEqual(guarded["farmer"], ["PICKUP", "CARROT", 1])
        self.assertEqual(guarded["hands"], [["PASS"]])

    def test_sequential_inspection_and_guard_do_not_mutate_observation(self):
        obs = observation(farmer=(2, 2), hand_positions=[(2, 2)])
        obs["farms"][0]["tiles"][2][2] = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "watered_today": False,
            "yield_units": 1,
            "fertilized_until_day": -1,
        }
        original = copy.deepcopy(obs)
        action = {
            "farmer": ["WATER"],
            "hands": [["WATER"]],
            "market": [],
        }

        issues = inspect_action(obs, action)
        guarded = guard_action(obs, action)

        self.assertEqual(
            [(issue.code, issue.path) for issue in issues],
            [("unit.no_effect", "$.hands[0]")],
        )
        self.assertEqual(guarded["hands"], [["PASS"]])
        self.assertEqual(obs, original)

    def test_reports_inventory_destroyed_by_a_shed_overflow(self):
        obs = observation(farmer=(4, 4))
        obs["private"]["shed"] = {"WHEAT": 99}
        obs["private"]["inventories"][0] = {"CARROT": 3}

        issues = inspect_action(
            obs,
            {"farmer": ["DROP"], "hands": [], "market": []},
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "LOSSY")
        self.assertEqual(issues[0].code, "shed.drop_overflow")
        self.assertEqual(issues[0].path, "$.farmer")
        self.assertIn("2", issues[0].message)

    def test_guard_blocks_a_drop_that_would_destroy_inventory(self):
        obs = observation(farmer=(4, 4))
        obs["private"]["shed"] = {"WHEAT": 99}
        obs["private"]["inventories"][0] = {"CARROT": 3}

        guarded = guard_action(
            obs,
            {"farmer": ["DROP"], "hands": [], "market": []},
        )

        self.assertEqual(guarded["farmer"], ["PASS"])

    def test_guard_reprojects_later_units_after_blocking_a_lossy_drop(self):
        obs = observation(farmer=(4, 4), hand_positions=[(4, 4)])
        obs["private"]["shed"] = {"WHEAT": 99}
        obs["private"]["inventories"] = [
            {"CARROT": 2},
            {"MELON": 1},
        ]
        action = {
            "farmer": ["DROP"],
            "hands": [["DROP"]],
            "market": [],
        }

        guarded = guard_action(obs, action)

        self.assertEqual(guarded["farmer"], ["PASS"])
        self.assertEqual(guarded["hands"], [["DROP"]])

    def test_guard_keeps_a_drop_that_fits_in_the_shed(self):
        obs = observation(farmer=(4, 4))
        obs["private"]["shed"] = {"WHEAT": 98}
        obs["private"]["inventories"][0] = {"CARROT": 2}
        action = {"farmer": ["DROP"], "hands": [], "market": []}

        self.assertEqual(inspect_action(obs, action), ())
        self.assertEqual(guard_action(obs, action), action)

    def test_reports_and_blocks_fertilizer_that_adds_no_coverage(self):
        obs = observation(farmer=(2, 2))
        obs["farms"][0]["tiles"][2][2] = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "watered_today": False,
            "yield_units": 1,
            "fertilized_until_day": 2,
        }
        obs["private"]["inventories"][0] = {"FERTILIZER": 1}
        action = {"farmer": ["FERTILIZE"], "hands": [], "market": []}

        issues = inspect_action(obs, action)
        guarded = guard_action(obs, action)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "LOSSY")
        self.assertEqual(issues[0].code, "fertilize.redundant")
        self.assertEqual(issues[0].path, "$.farmer")
        self.assertEqual(guarded["farmer"], ["PASS"])


if __name__ == "__main__":
    unittest.main()
