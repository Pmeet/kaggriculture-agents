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
import statistics
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402

# Fewer than this decides nothing. A 24-seed paired match (48 games) already
# carries a +/-0.19 interval on win rate; at 10 seeds the interval is wider than
# any improvement we have ever shipped, and the same candidate has scored 0.900
# on one 5-seed set and 0.750 on another. Twenty is the floor, not the target --
# 40+ for anything heading to the ladder.
MIN_SEEDS = 20


def evaluate(module, params, opponent, seeds, workers):
    spec = {"module": module, "attr": "make_agent", "params": params, "name": "cand"}
    report = run_match(spec, opponent, seeds, workers=workers)
    return report, report.mean_bank - report.mean_opponent_bank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="main")
    parser.add_argument("--opponent", default="recent",
                        help="comma-separated: 'recent' / 'recent:N' (the last N "
                             "submissions, default), 'benchmarks', a version label "
                             "(v21), an inclusive range (v18..v21), or module:attr")
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--allow-small", action="store_true",
                        help=f"permit fewer than {MIN_SEEDS} seeds (debugging only)")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--variant", action="append", default=[],
                        help="name:{json} , repeatable")
    args = parser.parse_args()
    if args.seeds < MIN_SEEDS and not args.allow_small:
        print(f"{args.seeds} seeds is {MIN_SEEDS * 2 - args.seeds * 2} games short of the "
              f"{MIN_SEEDS}-seed floor; raising to {MIN_SEEDS}. "
              f"Pass --allow-small to override.")
        args.seeds = MIN_SEEDS

    import importlib
    module = importlib.import_module(args.module)
    search = range(1, args.seeds + 1)
    holdout = range(1001, 1001 + args.seeds)

    from lab.versions import expand
    opponents = expand(args.opponent)
    labels = [o["name"] if isinstance(o, dict) else o for o in opponents]

    print(f"{args.module} vs {', '.join(labels)}  "
          f"{args.seeds} seeds x 2 seats, held out on {args.seeds} more")
    for spec in args.variant:
        name, _, blob = spec.partition(":")
        params = dict(module.DEFAULTS)
        params.update(json.loads(blob or "{}"))
        per = []
        clean = True
        for opponent in opponents:
            sr, sm = evaluate(args.module, params, opponent, search, args.workers)
            hr, hm = evaluate(args.module, params, opponent, holdout, args.workers)
            clean = clean and sr.clean and hr.clean
            per.append((sr.score, sm, hr.score, hm, sr.mean_bank))
        mean = [statistics.fmean(c) for c in zip(*per)]
        detail = "  ".join(f"{lab}:{p[3]:>+7,.0f}" for lab, p in zip(labels, per))
        print(f"{name:<22} search {mean[0]:.3f} margin {mean[1]:>+9,.0f}   "
              f"holdout {mean[2]:.3f} margin {mean[3]:>+9,.0f}   "
              f"[{detail}]{'' if clean else '  ISSUES'}")


if __name__ == "__main__":
    main()
