"""Pull replays of the current top ladder teams, so the pool can stop being us.

Every opponent we can play locally descends from our own ideas, which is why the
gauntlet reads 1.000 while the ladder reads ~0.5. The only unbiased sample of
what beats us is what the top of the board actually does, and those replays are
public.

The route is not obvious, because `ListEpisodes` needs a submission id and the
leaderboard only gives team ids. `ListTeamPublicSubmissions` bridges the two, and
it needs a browser session (cookie + XSRF header), not the API token -- the token
authenticates `competitions` endpoints but not these internal ones.

    python lab/scout.py --top 20            # list who they are, download nothing
    python lab/scout.py --top 20 --download # one replay each into replays/top/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

API = "https://www.kaggle.com/api/i"
COMPETITION_ID = 100801
OUT_DIR = os.path.join(REPO, "replays", "top")


def session():
    """A browser session: cookie jar plus the XSRF token that must echo it."""
    jar = "/tmp/kaggle_scout_cookies.txt"
    subprocess.run(["curl", "-sS", "-c", jar,
                    "https://www.kaggle.com/competitions/kaggriculture/leaderboard",
                    "-o", os.devnull], check=True)
    token = ""
    with open(jar) as handle:
        for line in handle:
            if "XSRF-TOKEN" in line:
                token = line.split()[-1]
    if not token:
        raise SystemExit("no XSRF token; Kaggle may have changed the leaderboard page")
    return jar, token


def call(jar, token, path, body):
    out = subprocess.run(
        ["curl", "-sS", "-b", jar, "-X", "POST", f"{API}/{path}",
         "-H", "Content-Type: application/json", "-H", f"x-xsrf-token: {token}",
         "--data-binary", json.dumps(body)],
        capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def leaderboard(top):
    """(team_id, name, score) for the top N, via the authenticated CLI."""
    env = dict(os.environ)
    env["KAGGLE_API_TOKEN"] = open(
        os.path.expanduser("~/.kaggle/access_token")).read().strip()
    out = subprocess.run(
        [os.path.expanduser("~/.venvs/kaggri/bin/kaggle"), "competitions",
         "leaderboard", "kaggriculture", "--show",
         "--page-size", str(max(top, 20)), "--format", "csv"],
        capture_output=True, text=True, env=env).stdout
    rows = []
    for line in out.splitlines():
        if not re.match(r"^\d+,", line):
            continue
        parts = line.split(",")
        try:
            rows.append((parts[0], ",".join(parts[1:-2]), float(parts[-1])))
        except ValueError:
            continue
    return rows[:top]


def best_submission(jar, token, team_id):
    data = call(jar, token, "competitions.SubmissionService/ListTeamPublicSubmissions",
                {"teamId": int(team_id)})
    best, best_score = None, float("-inf")
    for sub in data.get("submissions", []):
        try:
            score = float(sub.get("publicScoreFormatted", "nan"))
        except ValueError:
            continue
        if score > best_score:
            best, best_score = sub.get("id"), score
    return best, best_score


def an_episode(submission_id):
    """One completed episode for a submission, preferring the most recent."""
    out = subprocess.run(
        ["curl", "-sS", "-X", "POST",
         f"{API}/competitions.EpisodeService/ListEpisodes",
         "-H", "Content-Type: application/json",
         "--data-binary", json.dumps({"submissionId": int(submission_id)})],
        capture_output=True, text=True).stdout
    try:
        episodes = json.loads(out).get("episodes", [])
    except json.JSONDecodeError:
        return None
    done = [e for e in episodes if e.get("state") == "COMPLETED"]
    if not done:
        return None
    done.sort(key=lambda e: e.get("endTime") or "", reverse=True)
    return done[0].get("id")


def download(episode_id):
    env = dict(os.environ)
    env["KAGGLE_API_TOKEN"] = open(
        os.path.expanduser("~/.kaggle/access_token")).read().strip()
    os.makedirs(OUT_DIR, exist_ok=True)
    subprocess.run(
        [os.path.expanduser("~/.venvs/kaggri/bin/kaggle"), "competitions", "replay",
         str(episode_id), "-p", OUT_DIR],
        capture_output=True, text=True, env=env)
    path = os.path.join(OUT_DIR, f"episode-{episode_id}-replay.json")
    return path if os.path.exists(path) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()

    jar, token = session()
    rows = leaderboard(args.top)
    print(f"{'#':>3} {'team':<26}{'rating':>9}{'submission':>12}{'episode':>11}  file")
    index = {}
    for i, (team_id, name, score) in enumerate(rows, 1):
        sub, _sub_score = best_submission(jar, token, team_id)
        episode = an_episode(sub) if sub else None
        path = ""
        if episode and args.download:
            got = download(episode)
            path = os.path.basename(got) if got else "FAILED"
        print(f"{i:>3} {name[:25]:<26}{score:>9.1f}{str(sub or '-'):>12}"
              f"{str(episode or '-'):>11}  {path}")
        if episode:
            index[str(episode)] = {"team": name, "team_id": team_id,
                                   "rating": score, "submission": sub}
    if args.download and index:
        with open(os.path.join(OUT_DIR, "index.json"), "w") as handle:
            json.dump(index, handle, indent=2)
        print(f"\nindex written to {os.path.join(OUT_DIR, 'index.json')}")


if __name__ == "__main__":
    main()
