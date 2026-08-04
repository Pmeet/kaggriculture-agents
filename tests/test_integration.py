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
