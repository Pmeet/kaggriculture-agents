import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TournamentCliTest(unittest.TestCase):
    def test_runs_a_paired_seed_and_writes_reports(self):
        root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as temporary_directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "kaggriculture_harness.cli",
                    "--candidate",
                    str(root / "main.py"),
                    "--opponent",
                    "pass",
                    "--seeds",
                    "31",
                    "--output",
                    temporary_directory,
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            report_path = Path(temporary_directory) / "report.json"
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(report_path.is_file())
            self.assertTrue((Path(temporary_directory) / "games.csv").is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["summary"]["games"], 2)
        self.assertIn("2 games", completed.stdout)


if __name__ == "__main__":
    unittest.main()
