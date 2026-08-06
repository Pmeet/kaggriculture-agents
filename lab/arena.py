"""Fast in-process paired arena for Kaggriculture agents.

The competition harness in ``kaggriculture_harness`` runs agents from files and
validates their action shape; it is the pre-submission gate. This module is the
research loop: it imports agents as callables, runs games in worker processes,
and reports paired win rates. On a 32-core box it sustains ~25 games/sec.

An agent spec is either:

* a built-in name -- ``"starter"``, ``"random"``, ``"pass"``;
* ``"module:attr"`` -- imported and used directly if it is an agent callable,
  or called with the params dict if it is a factory named ``make_agent``;
* a dict ``{"module": ..., "attr": ..., "params": {...}, "name": ...}``.
"""

from __future__ import annotations

import importlib
import math
import os
import statistics
import sys
import time
import warnings
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILTIN_AGENTS = ("starter", "random", "pass")

_AGENT_CACHE: dict[str, Callable] = {}


def _quiet_imports() -> None:
    """kaggle-environments prints unrelated OpenSpiel/CABT loader noise on import."""
    warnings.filterwarnings("ignore")
    os.environ.setdefault("PYTHONWARNINGS", "ignore")


def normalize_spec(spec: Any) -> dict:
    """Turn any accepted spec form into a canonical dict."""
    if isinstance(spec, dict):
        out = dict(spec)
        out.setdefault("params", None)
        out.setdefault("name", out.get("attr") or out.get("module") or "agent")
        return out
    if isinstance(spec, str):
        if spec in BUILTIN_AGENTS:
            return {"builtin": spec, "params": None, "name": spec}
        module, _, attr = spec.partition(":")
        attr = attr or "agent"
        return {"module": module, "attr": attr, "params": None, "name": spec}
    raise TypeError(f"unsupported agent spec: {spec!r}")


def spec_key(spec: dict) -> str:
    if "builtin" in spec:
        return spec["builtin"]
    return repr((spec.get("module"), spec.get("attr"), sorted((spec.get("params") or {}).items())))


def resolve_agent(spec: dict) -> Any:
    """Build (and memoize) the callable for a spec inside the current process."""
    key = spec_key(spec)
    cached = _AGENT_CACHE.get(key)
    if cached is not None:
        return cached
    if "builtin" in spec:
        _AGENT_CACHE[key] = spec["builtin"]
        return spec["builtin"]
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    module = importlib.import_module(spec["module"])
    target = getattr(module, spec.get("attr") or "agent")
    params = spec.get("params")
    if params is not None:
        target = target(params)
    _AGENT_CACHE[key] = target
    return target


@dataclass
class GameResult:
    seed: int
    seat: int  # seat the candidate occupied
    candidate_bank: float
    opponent_bank: float
    candidate_status: str
    opponent_status: str
    max_step_seconds: float
    mean_step_seconds: float
    error: str = ""

    @property
    def outcome(self) -> int:
        """1 candidate win, 0 tie, -1 loss. Engine errors count as a loss."""
        if self.candidate_status != "DONE":
            return -1
        if self.opponent_status != "DONE":
            return 1
        if self.candidate_bank > self.opponent_bank:
            return 1
        if self.candidate_bank < self.opponent_bank:
            return -1
        return 0


def play_game(candidate: Any, opponent: Any, seed: int, seat: int) -> GameResult:
    """Run one full episode with the candidate in ``seat``."""
    _quiet_imports()
    from kaggle_environments import make

    cand_spec = normalize_spec(candidate)
    opp_spec = normalize_spec(opponent)
    agents: list[Any] = [None, None]
    agents[seat] = resolve_agent(cand_spec)
    agents[1 - seat] = resolve_agent(opp_spec)

    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    error = ""
    try:
        env.run(agents)
    except Exception as exc:  # pragma: no cover - defensive
        error = f"{type(exc).__name__}: {exc}"

    final = env.steps[-1]
    banks = [float(s.reward) if s.reward is not None else 0.0 for s in final]
    statuses = [str(s.status) for s in final]

    durations: list[float] = []
    for entry in env.logs or []:
        record = entry[seat] if isinstance(entry, (list, tuple)) and len(entry) > seat else None
        if isinstance(record, dict) and record.get("duration") is not None:
            durations.append(float(record["duration"]))
        if isinstance(record, dict) and record.get("stderr"):
            error = error or record["stderr"].strip().splitlines()[-1][:300]

    return GameResult(
        seed=seed,
        seat=seat,
        candidate_bank=banks[seat],
        opponent_bank=banks[1 - seat],
        candidate_status=statuses[seat],
        opponent_status=statuses[1 - seat],
        max_step_seconds=max(durations) if durations else 0.0,
        mean_step_seconds=statistics.fmean(durations) if durations else 0.0,
        error=error,
    )


def _worker(job: tuple) -> GameResult:
    candidate, opponent, seed, seat = job
    return play_game(candidate, opponent, seed, seat)


@dataclass
class MatchReport:
    candidate: str
    opponent: str
    games: list[GameResult] = field(default_factory=list)
    wall_seconds: float = 0.0

    @property
    def wins(self) -> int:
        return sum(1 for g in self.games if g.outcome > 0)

    @property
    def losses(self) -> int:
        return sum(1 for g in self.games if g.outcome < 0)

    @property
    def ties(self) -> int:
        return sum(1 for g in self.games if g.outcome == 0)

    @property
    def score(self) -> float:
        """Win rate counting a tie as half a win."""
        if not self.games:
            return 0.0
        return (self.wins + 0.5 * self.ties) / len(self.games)

    @property
    def wilson(self) -> tuple[float, float]:
        """95% Wilson interval around ``score``."""
        n = len(self.games)
        if n == 0:
            return (0.0, 0.0)
        z = 1.96
        p = self.score
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
        return (max(0.0, center - margin), min(1.0, center + margin))

    @property
    def mean_bank(self) -> float:
        return statistics.fmean(g.candidate_bank for g in self.games) if self.games else 0.0

    @property
    def mean_opponent_bank(self) -> float:
        return statistics.fmean(g.opponent_bank for g in self.games) if self.games else 0.0

    @property
    def errors(self) -> list[str]:
        return sorted({g.error for g in self.games if g.error})

    @property
    def max_step_seconds(self) -> float:
        return max((g.max_step_seconds for g in self.games), default=0.0)

    @property
    def clean(self) -> bool:
        return all(
            g.candidate_status == "DONE" and g.opponent_status == "DONE" and not g.error
            for g in self.games
        )

    def summary(self) -> str:
        lo, hi = self.wilson
        return (
            f"{self.candidate} vs {self.opponent}: "
            f"{self.wins}W/{self.losses}L/{self.ties}T  "
            f"score={self.score:.3f} [{lo:.3f},{hi:.3f}]  "
            f"bank {self.mean_bank:,.0f} vs {self.mean_opponent_bank:,.0f}  "
            f"maxstep={self.max_step_seconds * 1000:.0f}ms  "
            f"{len(self.games)} games in {self.wall_seconds:.1f}s"
            + ("" if self.clean else f"  ISSUES: {self.errors[:2]}")
        )


def run_match(
    candidate: Any,
    opponent: Any,
    seeds: Iterable[int],
    workers: int | None = None,
    both_seats: bool = True,
) -> MatchReport:
    """Play ``seeds`` (from both seats by default) and aggregate."""
    seeds = list(seeds)
    seats: Sequence[int] = (0, 1) if both_seats else (0,)
    jobs = [(candidate, opponent, seed, seat) for seed in seeds for seat in seats]
    workers = workers or min(len(jobs), max(1, (os.cpu_count() or 4) - 2))

    started = time.time()
    if workers <= 1:
        results = [_worker(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_worker, jobs, chunksize=1))

    report = MatchReport(
        candidate=normalize_spec(candidate)["name"],
        opponent=normalize_spec(opponent)["name"],
        games=results,
        wall_seconds=time.time() - started,
    )
    return report


def run_gauntlet(
    candidate: Any,
    opponents: Sequence[Any],
    seeds: Iterable[int],
    workers: int | None = None,
) -> list[MatchReport]:
    """Play the candidate against every opponent over the same seeds."""
    seeds = list(seeds)
    return [run_match(candidate, opp, seeds, workers=workers) for opp in opponents]
