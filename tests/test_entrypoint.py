import importlib.util
import unittest
from pathlib import Path

from kaggle_environments.agent import get_last_callable


class AgentEntrypointTest(unittest.TestCase):
    def test_main_exposes_callable_agent(self):
        entrypoint = Path(__file__).resolve().parents[1] / "main.py"

        self.assertTrue(entrypoint.is_file(), "main.py must exist at the submission root")

        spec = importlib.util.spec_from_file_location("submission_main", entrypoint)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(callable(getattr(module, "agent", None)))

    def test_kaggle_loader_selects_agent(self):
        entrypoint = Path(__file__).resolve().parents[1] / "main.py"
        source = entrypoint.read_text(encoding="utf-8")

        loaded = get_last_callable(source, path=str(entrypoint))

        self.assertEqual(loaded.__name__, "agent")


if __name__ == "__main__":
    unittest.main()
