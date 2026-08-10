"""Pre-submission gate: run full episodes through the repo's action validator.

The validator in ``kaggriculture_harness`` knows the engine's sequential
semantics -- no-ops, atomic seed over-commitment, destructive overflow, the
ten-slot market rule -- and has caught several silent losses that cost real
money without ever raising an error.
"""

import collections
import os
import sys
import traceback
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kaggle_environments import make  # noqa: E402

import main  # noqa: E402
from kaggriculture_harness import actions as validator  # noqa: E402

counts = collections.Counter()
banks = []
crashes = []


def wrapped(obs):
    action = main.agent(obs)
    try:
        for issue in validator.inspect_action(obs, action):
            counts[f"{issue.severity}:{issue.code}"] += 1
    except Exception:
        if not crashes:
            crashes.append(traceback.format_exc())
    return action


for seed in (1, 2, 3, 4):
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    env.run([wrapped, "starter"])
    final = env.steps[-1]
    banks.append(final[0].reward)
    leftover = {k: v for k, v in final[0].observation["private"]["shed"].items() if v > 0}
    assert str(final[0].status) == "DONE", f"seed {seed} status {final[0].status}"
    assert not leftover, f"seed {seed} left {leftover} unsold"

print(f"banks {banks}")
print(f"issues {dict(counts) or 'none'}")
if crashes:
    print(crashes[0][-800:])
