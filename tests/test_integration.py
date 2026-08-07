import unittest
from pathlib import Path

from kaggle_environments import make


class AgentIntegrationTest(unittest.TestCase):
    def test_complete_episode_from_both_seats(self):
        entrypoint = Path(__file__).resolve().parents[1] / "main.py"

        for agents in ([str(entrypoint), "pass"], ["pass", str(entrypoint)]):
            with self.subTest(agents=agents):
                environment = make(
                    "kaggriculture",
                    configuration={"seed": 17},
                    debug=True,
                )
                environment.run(agents)

                statuses = [state.status for state in environment.steps[-1]]
                self.assertEqual(statuses, ["DONE", "DONE"])


if __name__ == "__main__":
    unittest.main()


class FastRunnerParityTest(unittest.TestCase):
    """The research loop must not measure a different game from the real one."""

    def test_fast_runner_matches_env_run(self):
        from lab.arena import fast_play, play_game

        candidate = {"module": "main", "attr": "agent", "name": "main"}
        for seed, seat in ((1, 0), (2, 1)):
            official = play_game(candidate, "starter", seed, seat)
            lean = fast_play(candidate, "starter", seed, seat)
            self.assertEqual(official.candidate_bank, lean.candidate_bank,
                             f"seed {seed} seat {seat}")
            self.assertEqual(official.opponent_bank, lean.opponent_bank,
                             f"seed {seed} seat {seat}")
            self.assertEqual(official.candidate_status, lean.candidate_status)
