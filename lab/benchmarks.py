"""Pick the benchmark opponents from the live leaderboard, not from memory.

A benchmark set chosen by hand goes stale the moment a newer agent climbs past
it, and then every measurement is taken against something we already beat. This
reads our own submissions' live ratings, keeps the strongest that have a frozen
snapshot on disk, and writes them where `lab/pool.py` picks them up.

Two guards matter more than the ranking:

* **Minimum games.** A submission seeds at 600 and climbs for hours. Ranking on
  a rating with nine games behind it promotes noise, and demotes an agent that
  has actually proved itself. `--min-games` is the floor.
* **Frozen snapshot required.** A rating is only useful as a benchmark if the
  exact code is still runnable, so a submission with no `agents/baseline_*.py`
  is skipped rather than guessed at.

    python lab/benchmarks.py                # show the standings
    python lab/benchmarks.py --refresh      # rewrite lab/benchmarks.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

REGISTRY = os.path.join(HERE, "submissions.json")
OUTPUT = os.path.join(HERE, "benchmarks.json")
EPISODES = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
TEAM = 16659125


def live_ratings():
    """Rating per submission, straight from the competition API."""
    token = open(os.path.expanduser("~/.kaggle/access_token")).read().strip()
    env = dict(os.environ, KAGGLE_API_TOKEN=token)
    out = subprocess.run(
        [os.path.expanduser("~/.venvs/kaggri/bin/kaggle"),
         "competitions", "submissions", "kaggriculture"],
        capture_output=True, text=True, env=env).stdout
    ratings = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        try:
            ratings[parts[0]] = float(parts[-1])
        except ValueError:
            continue
    return ratings


def game_count(submission_id):
    body = json.dumps({"submissionId": int(submission_id)})
    out = subprocess.run(
        ["curl", "-sS", "-X", "POST", EPISODES,
         "-H", "Content-Type: application/json", "--data-binary", body],
        capture_output=True, text=True).stdout
    try:
        episodes = json.loads(out).get("episodes", [])
    except json.JSONDecodeError:
        return 0
    return sum(1 for e in episodes if e.get("state") == "COMPLETED")


def standings(min_games):
    registry = json.load(open(REGISTRY))
    ratings = live_ratings()
    rows = []
    for sub, entry in registry.items():
        module = entry["agent"]
        path = os.path.join(REPO, module.replace(".", os.sep) + ".py")
        if not os.path.exists(path):
            continue
        rating = ratings.get(sub)
        if rating is None:
            continue
        rows.append({
            "submission": sub,
            "label": entry["label"],
            "agent": module,
            "rating": rating,
            "games": game_count(sub),
        })
    rows.sort(key=lambda r: -r["rating"])
    for row in rows:
        row["eligible"] = row["games"] >= min_games
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=2)
    parser.add_argument("--min-games", type=int, default=25)
    parser.add_argument("--refresh", action="store_true",
                        help="write lab/benchmarks.json")
    args = parser.parse_args()

    rows = standings(args.min_games)
    print(f"{'':2}{'ver':<6}{'rating':>9}{'games':>7}  {'agent':<24}")
    for row in rows:
        mark = "* " if row["eligible"] else "  "
        print(f"{mark}{row['label']:<6}{row['rating']:>9.1f}{row['games']:>7}  "
              f"{row['agent']:<24}"
              f"{'' if row['eligible'] else '  (too few games)'}")

    chosen = [r for r in rows if r["eligible"]][: args.top]
    print()
    print("benchmarks:", ", ".join(f"{r['label']} @ {r['rating']:.1f}" for r in chosen))
    if args.refresh:
        with open(OUTPUT, "w") as handle:
            json.dump([{"module": r["agent"], "attr": "agent",
                        "name": f"{r['label']}@{r['rating']:.0f}"}
                       for r in chosen], handle, indent=2)
        print(f"written to {OUTPUT}")


if __name__ == "__main__":
    main()
