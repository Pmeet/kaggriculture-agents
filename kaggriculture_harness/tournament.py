import csv
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib import metadata
from math import ceil, sqrt
from pathlib import Path
from time import perf_counter
from typing import Literal


@dataclass(frozen=True)
class GameResult:
    seed: int
    candidate_seat: int
    statuses: tuple[str, str]
    candidate_reward: float
    opponent_reward: float
    outcome: Literal["win", "loss", "tie"]
    steps: int
    elapsed_seconds: float
    action_calls: int
    issue_count: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_max_ms: float


@dataclass(frozen=True)
class TournamentResult:
    games: tuple[GameResult, ...]
    candidate_sha256: str | None = None
    opponent_sha256: str | None = None
    engine_sha256: str | None = None
    kaggle_environments_version: str | None = None
    python_version: str | None = None


@dataclass(frozen=True)
class TournamentSummary:
    games: int
    wins: int
    losses: int
    ties: int
    score_rate: float
    decisive_win_rate: float | None
    decisive_win_rate_ci95: tuple[float, float] | None
    seat_0_score_rate: float
    seat_1_score_rate: float
    seat_delta: float
    mean_reward_margin: float
    all_done_games: int
    total_issue_count: int
    max_latency_ms: float
    max_game_p95_latency_ms: float


@dataclass(frozen=True)
class ReportPaths:
    json_path: Path
    csv_path: Path


def _score(outcome: str) -> float:
    if outcome == "win":
        return 1.0
    if outcome == "tie":
        return 0.5
    return 0.0


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    probability = successes / total
    denominator = 1 + z**2 / total
    center = (probability + z**2 / (2 * total)) / denominator
    margin = (
        z
        * sqrt((probability * (1 - probability) + z**2 / (4 * total)) / total)
        / denominator
    )
    return center - margin, center + margin


def _percentile(samples: list[float], probability: float) -> float:
    ordered = sorted(samples)
    index = max(0, ceil(probability * len(ordered)) - 1)
    return ordered[index]


def summarize_tournament(tournament: TournamentResult) -> TournamentSummary:
    games = tournament.games
    if not games:
        raise ValueError("A tournament summary requires at least one game")

    wins = sum(game.outcome == "win" for game in games)
    losses = sum(game.outcome == "loss" for game in games)
    ties = sum(game.outcome == "tie" for game in games)
    decisive_games = wins + losses
    seat_0_games = [game for game in games if game.candidate_seat == 0]
    seat_1_games = [game for game in games if game.candidate_seat == 1]
    seat_0_score_rate = sum(_score(game.outcome) for game in seat_0_games) / len(
        seat_0_games
    )
    seat_1_score_rate = sum(_score(game.outcome) for game in seat_1_games) / len(
        seat_1_games
    )

    return TournamentSummary(
        games=len(games),
        wins=wins,
        losses=losses,
        ties=ties,
        score_rate=sum(_score(game.outcome) for game in games) / len(games),
        decisive_win_rate=wins / decisive_games if decisive_games else None,
        decisive_win_rate_ci95=(
            _wilson_interval(wins, decisive_games) if decisive_games else None
        ),
        seat_0_score_rate=seat_0_score_rate,
        seat_1_score_rate=seat_1_score_rate,
        seat_delta=seat_0_score_rate - seat_1_score_rate,
        mean_reward_margin=sum(
            game.candidate_reward - game.opponent_reward for game in games
        )
        / len(games),
        all_done_games=sum(game.statuses == ("DONE", "DONE") for game in games),
        total_issue_count=sum(game.issue_count for game in games),
        max_latency_ms=max(game.latency_max_ms for game in games),
        max_game_p95_latency_ms=max(game.latency_p95_ms for game in games),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_tournament_report(
    tournament: TournamentResult,
    destination: Path,
    candidate: str | Path,
    opponent: str | Path,
) -> ReportPaths:
    candidate_path = Path(candidate).resolve()
    distribution = metadata.distribution("kaggle-environments")
    engine_path = Path(
        distribution.locate_file(
            "kaggle_environments/envs/kaggriculture/kaggriculture.py"
        )
    )
    current_candidate_sha256 = _sha256(candidate_path)
    if (
        tournament.candidate_sha256 is not None
        and tournament.candidate_sha256 != current_candidate_sha256
    ):
        raise RuntimeError("Candidate source changed after the tournament run")
    current_engine_sha256 = _sha256(engine_path)
    if (
        tournament.engine_sha256 is not None
        and tournament.engine_sha256 != current_engine_sha256
    ):
        raise RuntimeError("Kaggriculture engine changed after the tournament run")

    report_metadata = {
        "python_version": tournament.python_version or platform.python_version(),
        "kaggle_environments_version": (
            tournament.kaggle_environments_version or distribution.version
        ),
        "engine_sha256": tournament.engine_sha256 or current_engine_sha256,
        "candidate_sha256": (
            tournament.candidate_sha256 or current_candidate_sha256
        ),
        "opponent_sha256": tournament.opponent_sha256,
    }
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "candidate": str(candidate_path),
        "opponent": str(opponent),
        "metadata": report_metadata,
        "summary": asdict(summarize_tournament(tournament)),
        "games": [asdict(game) for game in tournament.games],
    }

    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "report.json"
    csv_path = destination / "games.csv"
    with json_path.open("w", encoding="utf-8", newline="\n") as report_file:
        json.dump(report, report_file, indent=2, sort_keys=True)
        report_file.write("\n")

    fieldnames = [
        "seed",
        "candidate_seat",
        "status_0",
        "status_1",
        "candidate_reward",
        "opponent_reward",
        "reward_margin",
        "outcome",
        "steps",
        "elapsed_seconds",
        "action_calls",
        "issue_count",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_max_ms",
        "python_version",
        "kaggle_environments_version",
        "engine_sha256",
        "candidate_sha256",
        "opponent_sha256",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as games_file:
        writer = csv.DictWriter(games_file, fieldnames=fieldnames)
        writer.writeheader()
        for game in tournament.games:
            writer.writerow(
                {
                    "seed": game.seed,
                    "candidate_seat": game.candidate_seat,
                    "status_0": game.statuses[0],
                    "status_1": game.statuses[1],
                    "candidate_reward": game.candidate_reward,
                    "opponent_reward": game.opponent_reward,
                    "reward_margin": game.candidate_reward - game.opponent_reward,
                    "outcome": game.outcome,
                    "steps": game.steps,
                    "elapsed_seconds": game.elapsed_seconds,
                    "action_calls": game.action_calls,
                    "issue_count": game.issue_count,
                    "latency_p50_ms": game.latency_p50_ms,
                    "latency_p95_ms": game.latency_p95_ms,
                    "latency_max_ms": game.latency_max_ms,
                    **report_metadata,
                }
            )

    return ReportPaths(json_path=json_path, csv_path=csv_path)


def run_paired_tournament(
    candidate: str | Path,
    opponent: str | Path,
    seeds: list[int],
) -> TournamentResult:
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable

    from kaggriculture_harness.actions import inspect_action

    games = []
    candidate_path = Path(candidate).resolve()
    candidate_bytes = candidate_path.read_bytes()
    candidate_source = candidate_bytes.decode("utf-8")
    candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    opponent_path = Path(opponent)
    if opponent_path.is_file():
        opponent_path = opponent_path.resolve()
        opponent_bytes = opponent_path.read_bytes()
        opponent_source = opponent_bytes.decode("utf-8")
        opponent_sha256 = hashlib.sha256(opponent_bytes).hexdigest()
    else:
        opponent_source = None
        opponent_sha256 = None
    distribution = metadata.distribution("kaggle-environments")
    engine_path = Path(
        distribution.locate_file(
            "kaggle_environments/envs/kaggriculture/kaggriculture.py"
        )
    )
    engine_sha256 = _sha256(engine_path)

    for seed in seeds:
        for candidate_seat in (0, 1):
            candidate_agent = get_last_callable(
                candidate_source,
                path=str(candidate_path),
            )
            latencies_ms = []
            issues = []

            def instrumented_agent(observation):
                action_started_at = perf_counter()
                candidate_action = candidate_agent(observation)
                latencies_ms.append((perf_counter() - action_started_at) * 1000)
                issues.extend(inspect_action(observation, candidate_action))
                return candidate_action

            if opponent_source is None:
                game_opponent = str(opponent)
            else:
                game_opponent = get_last_callable(
                    opponent_source,
                    path=str(opponent_path),
                )
            agents = [instrumented_agent, game_opponent]
            if candidate_seat == 1:
                agents.reverse()

            environment = make(
                "kaggriculture",
                configuration={"seed": seed},
                debug=True,
            )
            started_at = perf_counter()
            environment.run(agents)
            elapsed_seconds = perf_counter() - started_at
            final_states = environment.steps[-1]
            statuses = tuple(state.status for state in final_states)
            rewards = tuple(float(state.reward) for state in final_states)
            candidate_reward = rewards[candidate_seat]
            opponent_reward = rewards[1 - candidate_seat]
            if candidate_reward > opponent_reward:
                outcome = "win"
            elif candidate_reward < opponent_reward:
                outcome = "loss"
            else:
                outcome = "tie"
            games.append(
                GameResult(
                    seed=seed,
                    candidate_seat=candidate_seat,
                    statuses=statuses,
                    candidate_reward=candidate_reward,
                    opponent_reward=opponent_reward,
                    outcome=outcome,
                    steps=len(environment.steps),
                    elapsed_seconds=elapsed_seconds,
                    action_calls=len(latencies_ms),
                    issue_count=len(issues),
                    latency_p50_ms=_percentile(latencies_ms, 0.5),
                    latency_p95_ms=_percentile(latencies_ms, 0.95),
                    latency_max_ms=max(latencies_ms),
                )
            )

    return TournamentResult(
        games=tuple(games),
        candidate_sha256=candidate_sha256,
        opponent_sha256=opponent_sha256,
        engine_sha256=engine_sha256,
        kaggle_environments_version=distribution.version,
        python_version=platform.python_version(),
    )
