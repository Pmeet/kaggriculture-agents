"""Compare parameter variants of an agent over common random seeds.

Every variant plays the same seeds from both seats against the same opponent,
so differences are attributable to the parameters rather than to seed luck.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab.arena import run_match  # noqa: E402


def variant_spec(module, params, name):
    return {"module": module, "attr": "make_agent", "params": params, "name": name}


def compare(module, variants, opponent, seeds, workers=None, quiet=False):
    """``variants`` maps a label to a params-override dict."""
    rows = []
    for label, params in variants.items():
        report = run_match(
            variant_spec(module, params, label), opponent, seeds, workers=workers
        )
        rows.append((label, report))
        if not quiet:
            print(f"  {label:<28} {report.summary()}")
    rows.sort(key=lambda r: (-r[1].score, -r[1].mean_bank))
    return rows


def grid(**axes):
    """Cartesian product of parameter axes, labelled by their non-default values."""
    keys = list(axes)
    out = {}
    for combo in itertools.product(*(axes[k] for k in keys)):
        params = dict(zip(keys, combo))
        label = ",".join(f"{k}={v}" for k, v in params.items())
        out[label] = params
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", default="agents.v2")
    parser.add_argument("--opponent", default="agents.v1:agent")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--variants", default="{}",
                        help='JSON object mapping label -> params override')
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    variants = json.loads(args.variants)
    if not variants:
        variants = {"default": {}}
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    print(f"module={args.module} opponent={args.opponent} seeds={len(list(seeds))}x2")
    rows = compare(args.module, variants, args.opponent, seeds, workers=args.workers)
    print()
    print(f"{'variant':<32}{'score':>8}{'bank':>12}{'opp bank':>12}")
    for label, report in rows:
        print(f"{label:<32}{report.score:>8.3f}{report.mean_bank:>12,.0f}"
              f"{report.mean_opponent_bank:>12,.0f}")


if __name__ == "__main__":
    main()
