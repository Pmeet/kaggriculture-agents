import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kaggriculture_harness.tournament import (
    GameResult,
    TournamentResult,
    run_paired_tournament,
    summarize_tournament,
    write_tournament_report,
)


class PairedTournamentTest(unittest.TestCase):
    def test_runs_each_seed_from_both_candidate_seats(self):
        candidate = Path(__file__).resolve().parents[1] / "main.py"

        tournament = run_paired_tournament(
            candidate=candidate,
            opponent="pass",
            seeds=[17],
        )

        self.assertEqual(len(tournament.games), 2)
        self.assertEqual([game.candidate_seat for game in tournament.games], [0, 1])
        self.assertEqual([game.seed for game in tournament.games], [17, 17])
        self.assertTrue(
            all(game.statuses == ("DONE", "DONE") for game in tournament.games)
        )

    def test_records_results_from_the_candidate_perspective(self):
        candidate = Path(__file__).resolve().parents[1] / "main.py"

        tournament = run_paired_tournament(
            candidate=candidate,
            opponent="pass",
            seeds=[23],
        )

        for game in tournament.games:
            with self.subTest(candidate_seat=game.candidate_seat):
                self.assertGreater(game.candidate_reward, game.opponent_reward)
                self.assertEqual(game.outcome, "win")
                self.assertEqual(game.steps, 720)
                self.assertGreater(game.elapsed_seconds, 0)
                self.assertEqual(game.action_calls, 719)
                self.assertEqual(game.issue_count, 0)
                self.assertGreater(game.latency_max_ms, 0)
                self.assertLessEqual(game.latency_p50_ms, game.latency_p95_ms)
                self.assertLessEqual(game.latency_p95_ms, game.latency_max_ms)

    def test_summarizes_results_and_seat_delta(self):
        tournament = TournamentResult(
            games=(
                self._game(seat=0, outcome="win", candidate=10, opponent=5),
                self._game(seat=1, outcome="loss", candidate=3, opponent=4),
                self._game(seat=0, outcome="tie", candidate=2, opponent=2),
                self._game(seat=1, outcome="win", candidate=8, opponent=1),
            )
        )

        summary = summarize_tournament(tournament)

        self.assertEqual((summary.wins, summary.losses, summary.ties), (2, 1, 1))
        self.assertAlmostEqual(summary.score_rate, 0.625)
        self.assertAlmostEqual(summary.decisive_win_rate, 2 / 3)
        self.assertAlmostEqual(summary.decisive_win_rate_ci95[0], 0.2077, places=3)
        self.assertAlmostEqual(summary.decisive_win_rate_ci95[1], 0.9385, places=3)
        self.assertAlmostEqual(summary.seat_0_score_rate, 0.75)
        self.assertAlmostEqual(summary.seat_1_score_rate, 0.5)
        self.assertAlmostEqual(summary.seat_delta, 0.25)
        self.assertAlmostEqual(summary.mean_reward_margin, 2.75)
        self.assertEqual(summary.all_done_games, 4)
        self.assertEqual(summary.total_issue_count, 0)
        self.assertAlmostEqual(summary.max_latency_ms, 0.3)
        self.assertAlmostEqual(summary.max_game_p95_latency_ms, 0.2)

    def test_writes_json_and_csv_with_reproducibility_metadata(self):
        candidate = Path(__file__).resolve().parents[1] / "main.py"
        tournament = TournamentResult(
            games=(
                self._game(seat=0, outcome="win", candidate=10, opponent=5),
                self._game(seat=1, outcome="tie", candidate=6, opponent=6),
            )
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = write_tournament_report(
                tournament=tournament,
                destination=Path(temporary_directory),
                candidate=candidate,
                opponent="pass",
            )

            with paths.json_path.open(encoding="utf-8") as report_file:
                report = json.load(report_file)
            with paths.csv_path.open(encoding="utf-8", newline="") as games_file:
                rows = list(csv.DictReader(games_file))

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["summary"]["games"], 2)
        self.assertEqual(report["metadata"]["kaggle_environments_version"], "1.32.7")
        self.assertEqual(len(report["metadata"]["engine_sha256"]), 64)
        self.assertEqual(len(report["metadata"]["candidate_sha256"]), 64)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["outcome"], "win")
        self.assertEqual(rows[1]["candidate_seat"], "1")
        self.assertEqual(rows[0]["engine_sha256"], report["metadata"]["engine_sha256"])

    def test_rejects_a_candidate_changed_after_the_tournament(self):
        tournament = TournamentResult(
            games=(
                self._game(seat=0, outcome="tie", candidate=5, opponent=5),
                self._game(seat=1, outcome="tie", candidate=5, opponent=5),
            ),
            candidate_sha256="0" * 64,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory)
            candidate = destination / "main.py"
            candidate.write_text("def agent(obs):\n    return {}\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "changed"):
                write_tournament_report(
                    tournament=tournament,
                    destination=destination / "report",
                    candidate=candidate,
                    opponent="pass",
                )

    def test_snapshots_a_file_opponent_for_the_whole_tournament(self):
        root = Path(__file__).resolve().parents[1]

        with tempfile.TemporaryDirectory() as temporary_directory:
            opponent = Path(temporary_directory) / "opponent.py"
            replacement = "def agent(obs):\n    raise RuntimeError('changed')\n"
            source = (
                "_MUTATED = False\n\n"
                "def agent(obs):\n"
                "    global _MUTATED\n"
                "    if not _MUTATED:\n"
                "        _MUTATED = True\n"
                f"        with open({str(opponent)!r}, 'w', encoding='utf-8') as file:\n"
                f"            file.write({replacement!r})\n"
                "    hand_count = len(obs['farms'][obs['player']]['hands'])\n"
                "    return {'farmer': ['PASS'], "
                "'hands': [['PASS'] for _ in range(hand_count)], 'market': []}\n"
            )
            opponent.write_text(source, encoding="utf-8")
            original_hash = hashlib.sha256(opponent.read_bytes()).hexdigest()

            tournament = run_paired_tournament(
                candidate=root / "main.py",
                opponent=opponent,
                seeds=[37],
            )

        self.assertTrue(
            all(game.statuses == ("DONE", "DONE") for game in tournament.games)
        )
        self.assertEqual(
            tournament.opponent_sha256,
            original_hash,
        )

    def test_reports_no_decisive_rate_when_every_game_ties(self):
        tournament = TournamentResult(
            games=(
                self._game(seat=0, outcome="tie", candidate=4, opponent=4),
                self._game(seat=1, outcome="tie", candidate=5, opponent=5),
            )
        )

        summary = summarize_tournament(tournament)

        self.assertIsNone(summary.decisive_win_rate)
        self.assertIsNone(summary.decisive_win_rate_ci95)

    def test_rejects_an_empty_tournament_summary(self):
        with self.assertRaisesRegex(ValueError, "at least one game"):
            summarize_tournament(TournamentResult(games=()))

    @staticmethod
    def _game(seat, outcome, candidate, opponent):
        return GameResult(
            seed=1,
            candidate_seat=seat,
            statuses=("DONE", "DONE"),
            candidate_reward=candidate,
            opponent_reward=opponent,
            outcome=outcome,
            steps=720,
            elapsed_seconds=1.0,
            action_calls=719,
            issue_count=0,
            latency_p50_ms=0.1,
            latency_p95_ms=0.2,
            latency_max_ms=0.3,
        )


if __name__ == "__main__":
    unittest.main()
