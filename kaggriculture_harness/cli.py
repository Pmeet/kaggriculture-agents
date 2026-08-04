import argparse
from pathlib import Path

from kaggriculture_harness.tournament import (
    run_paired_tournament,
    summarize_tournament,
    write_tournament_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run paired-seat Kaggriculture games and write JSON/CSV reports."
    )
    parser.add_argument("--candidate", type=Path, default=Path("main.py"))
    parser.add_argument("--opponent", default="starter")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(1, 11)))
    parser.add_argument("--output", type=Path, default=Path("reports/latest"))
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    tournament = run_paired_tournament(
        candidate=arguments.candidate,
        opponent=arguments.opponent,
        seeds=arguments.seeds,
    )
    paths = write_tournament_report(
        tournament=tournament,
        destination=arguments.output,
        candidate=arguments.candidate,
        opponent=arguments.opponent,
    )
    summary = summarize_tournament(tournament)
    print(
        f"{summary.games} games: {summary.wins}W/{summary.losses}L/"
        f"{summary.ties}T; score rate {summary.score_rate:.3f}"
    )
    print(f"JSON: {paths.json_path}")
    print(f"CSV: {paths.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
