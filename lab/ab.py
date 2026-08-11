"""Head-to-head A/B of parameter settings against a frozen control agent.

Win rate over a few dozen games has a +/-0.19 interval, so the readable signal
is the paired bank margin under common random numbers. Every variant is played
against the *same* frozen opponent over the *same* seeds, from both seats, and
then re-checked on disjoint held-out seeds because anything selected on the
search seeds has been fitted to them.

    python lab/ab.py --opponent agents.baseline_i:agent \
        --variant 'control:{}' --variant 'fast6:{"early_cash_tiles":6}'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402


def evaluate(module, params, opponent, seeds, workers):
    spec = {"module": module, "attr": "make_agent", "params": params, "name": "cand"}
    report = run_match(spec, opponent, seeds, workers=workers)
    return report, report.mean_bank - report.mean_opponent_bank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="main")
    parser.add_argument("--opponent", default="agents.baseline_i:agent")
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--variant", action="append", default=[],
                        help="name:{json} , repeatable")
    args = parser.parse_args()

    import importlib
    module = importlib.import_module(args.module)
    search = range(1, args.seeds + 1)
    holdout = range(1001, 1001 + args.seeds)

    print(f"{args.module} vs {args.opponent}  "
          f"{args.seeds} seeds x 2 seats, held out on {args.seeds} more")
    for spec in args.variant:
        name, _, blob = spec.partition(":")
        overrides = json.loads(blob or "{}")
        params = dict(module.DEFAULTS)
        params.update(overrides)
        sr, sm = evaluate(args.module, params, args.opponent, search, args.workers)
        hr, hm = evaluate(args.module, params, args.opponent, holdout, args.workers)
        flag = "" if sr.clean and hr.clean else "  ISSUES"
        print(f"{name:<22} search {sr.score:.3f} margin {sm:>+9,.0f}   "
              f"holdout {hr.score:.3f} margin {hm:>+9,.0f}   "
              f"bank {sr.mean_bank:>8,.0f}{flag}")


if __name__ == "__main__":
    main()
