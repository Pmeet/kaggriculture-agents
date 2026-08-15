"""Guard the invariant that lets a version branch battle every earlier version.

Version branches are cut from `main` and inherit every frozen snapshot in
`agents/`, which is why work on v23 can be scored against v18-v21 without ever
switching branches. That only holds while the snapshots are immutable.

The failure this exists to catch is silent. Edit `agents/baseline_n.py` on a
version branch and every subsequent measurement "against v21" is really against
something else; no import fails, no test breaks, and the gauntlet reports a
number that looks exactly like the number it reported yesterday. It belongs to
the same family as the traps in AGENTS.md: a result that is wrong for a reason
unrelated to the change being measured.

So: `agents/` is append-only. Add a new frozen snapshot, never touch an old one.
Run this before trusting any cross-version result.

    python lab/checks/frozen.py            # against main
    python lab/checks/frozen.py --base v22 # against any other base

Exits non-zero if a frozen agent has drifted, so it can gate CI or a pre-push
hook.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

AGENT_DIR = "agents"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def resolve_base(base: str) -> str | None:
    """Prefer the local ref, fall back to the remote copy, else give up quietly."""
    for candidate in (base, f"origin/{base}"):
        try:
            git("rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}")
            return candidate
        except subprocess.CalledProcessError:
            continue
    return None


def frozen_drift(base_ref: str) -> tuple[list[str], list[str], list[str]]:
    """Split changes under agents/ into (modified, added, removed) since the fork point."""
    try:
        fork = git("merge-base", base_ref, "HEAD")
    except subprocess.CalledProcessError:
        fork = base_ref
    raw = git("diff", "--name-status", "--find-renames", fork, "HEAD", "--", AGENT_DIR)
    modified, added, removed = [], [], []
    for line in (ln for ln in raw.splitlines() if ln.strip()):
        parts = line.split("\t")
        status, paths = parts[0], parts[1:]
        if status.startswith("A"):
            added.append(paths[-1])
        elif status.startswith("D"):
            removed.append(paths[0])
        elif status.startswith("R"):
            # A rename is a delete as far as `agents.baseline_x` is concerned.
            removed.append(paths[0])
            added.append(paths[-1])
        else:
            modified.append(paths[0])
    return modified, added, removed


def referenced_agents() -> dict[str, str]:
    """Every agent the opponent set names, as {module: where it was named}."""
    out: dict[str, str] = {}
    lab = os.path.join(REPO_ROOT, "lab")
    for filename, extract in (
        ("benchmarks.json", lambda d: [e.get("module") for e in d]),
        ("submissions.json", lambda d: [e.get("agent") for e in d.values()]),
    ):
        path = os.path.join(lab, filename)
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        for module in extract(data):
            if module:
                out.setdefault(module, filename)
    return out


def check_importable(modules: dict[str, str]) -> list[str]:
    """An opponent that cannot be imported is an opponent silently dropped."""
    broken = []
    for module, source in sorted(modules.items()):
        try:
            mod = importlib.import_module(module)
        except Exception as exc:  # noqa: BLE001 - report, never crash the gate
            broken.append(f"{module} (named in {source}) failed to import: {exc}")
            continue
        if not any(hasattr(mod, attr) for attr in ("agent", "make_agent")):
            broken.append(f"{module} (named in {source}) has neither agent nor make_agent")
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", default="main",
                        help="ref the frozen agents must match (default: main)")
    args = parser.parse_args()

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    base_ref = resolve_base(args.base)
    if base_ref is None:
        print(f"frozen: base ref {args.base!r} not found locally; skipping the drift check")
        modified, added, removed = [], [], []
    else:
        modified, added, removed = frozen_drift(base_ref)
        print(f"frozen: {branch} against {base_ref}")

    referenced = referenced_agents()
    broken = check_importable(referenced)

    for path in added:
        print(f"   new     {path}")
    print(f"   checked {len(referenced)} referenced agent(s) from benchmarks.json "
          f"and submissions.json")

    problems = []
    for path in modified:
        problems.append(f"frozen agent modified: {path}")
    for path in removed:
        problems.append(f"frozen agent removed: {path}")
    problems.extend(broken)

    if problems:
        print()
        print("FAIL -- agents/ is append-only, and every named opponent must import.")
        for problem in problems:
            print(f"   {problem}")
        print()
        print("A modified snapshot makes every past measurement against it "
              "incomparable. Restore it and add a new file instead:")
        print(f"   git checkout {base_ref or 'main'} -- <path>")
        return 1

    print("OK -- every frozen agent matches the base, and every named opponent imports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
