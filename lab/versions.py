"""Resolve version labels (`v21`, `v18..v21`) to the frozen snapshots behind them.

`lab/submissions.json` already records which submission each label was, and
which `agents/baseline_*.py` still implements it. Everything else refers to
those agents by module path, which means writing `agents.baseline_k:agent` and
remembering that it is v18 -- easy to get wrong, and wrong silently, because the
mistaken module imports and plays perfectly well.

This is the lookup table, so a candidate can be scored against the versions it
actually has to beat without naming any of them:

    python lab/ab.py --variant 'cand:{}'              # the recent versions
    python lab/ab.py --opponent recent:7 --variant 'cand:{}'

`recent` is the point. Writing `v18..v21` into a script freezes the opponent set
at the day it was written: the moment v23 ships, every later candidate is still
being measured against agents it has already beaten, which is trap 5 in
AGENTS.md wearing a different hat. `recent` reads `submissions.json` and always
means the last N submissions, so the bar rises by itself.

A label only resolves while its snapshot is still on disk and unmodified, which
is what `lab/checks/frozen.py` enforces and why version branches are cut from
`main` rather than from each other.
"""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "submissions.json")

_LABEL = re.compile(r"^v(\d+)$")

# How many past submissions "recent" means when no count is given. Six spans
# roughly the last fortnight of work: wide enough that a candidate has to beat
# more than the current champion, narrow enough that it is not being graded
# against agents nobody would ship today.
RECENT_DEFAULT = 6


def registry() -> dict[str, str]:
    """{"v21": "agents.baseline_n:agent", ...}, newest label last."""
    try:
        with open(REGISTRY) as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    out = {}
    for entry in data.values():
        label, module = entry.get("label"), entry.get("agent")
        if label and module:
            out[label] = module if ":" in module else f"{module}:agent"
    return dict(sorted(out.items(), key=lambda kv: _order(kv[0])))


def _order(label: str) -> tuple[int, str]:
    match = _LABEL.match(label)
    return (int(match.group(1)), "") if match else (1 << 30, label)


def _range(lo: str, hi: str, table: dict[str, str]) -> list[str]:
    """Every known label between two, inclusive, in either written order."""
    bounds = sorted((_order(lo)[0], _order(hi)[0]))
    inside = [lab for lab in table if bounds[0] <= _order(lab)[0] <= bounds[1]]
    if not inside:
        raise KeyError(f"no known versions between {lo} and {hi}")
    return inside


def recent(count: int = RECENT_DEFAULT, table: dict[str, str] | None = None) -> list[str]:
    """The last `count` known version labels, oldest first.

    Derived from the registry every call, never written down, so adding v23 to
    `submissions.json` is the only step needed to start measuring against it.
    """
    table = registry() if table is None else table
    if count <= 0:
        raise ValueError(f"recent count must be positive, got {count}")
    return list(table)[-count:]


def _spec(label: str, table: dict[str, str]) -> dict:
    module, _, attr = table[label].partition(":")
    return {"module": module, "attr": attr, "name": label}


def expand(spec: str) -> list:
    """Turn a comma-separated opponent string into arena specs.

    Accepts `recent` / `recent:N` (the last N submissions), version labels
    (`v21`), inclusive ranges (`v18..v21`), the keyword `benchmarks`, and raw
    `module:attr` specs, mixed freely. Unknown tokens are passed through
    untouched so every existing invocation keeps working.
    """
    table = registry()
    out: list = []
    for token in (t.strip() for t in spec.split(",")):
        if not token:
            continue
        if token == "benchmarks":
            from lab.pool import BENCHMARKS
            out.extend(BENCHMARKS)
            continue
        if token == "recent" or token.startswith("recent:") or token.startswith("last:"):
            _, _, raw = token.partition(":")
            try:
                count = int(raw) if raw else RECENT_DEFAULT
            except ValueError:
                raise KeyError(f"{token!r}: expected recent:<number>") from None
            if not table:
                raise KeyError("submissions.json lists no versions, so 'recent' is empty")
            out.extend(_spec(label, table) for label in recent(count, table))
            continue
        if ".." in token:
            lo, _, hi = token.partition("..")
            out.extend(_spec(label, table) for label in _range(lo.strip(), hi.strip(), table))
            continue
        if token in table:
            out.append(_spec(token, table))
            continue
        if _LABEL.match(token):
            known = ", ".join(table) or "none"
            raise KeyError(f"unknown version {token!r}; submissions.json knows: {known}")
        out.append(token)
    return out


if __name__ == "__main__":
    for label, module in registry().items():
        print(f"{label:<6} {module}")
