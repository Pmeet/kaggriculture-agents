"""Market depth: what selling N units of a product actually earns.

Selling one unit adds one to the shared market inventory, which moves the price
down along that product's `above_func`. So the Nth unit is worth less than the
first, and for some products very much less. The shape parameter, not the base
price, is what decides whether a product can absorb volume:

    log    wheat, egg          sell 400 and the price is still 80% of base
    sqrt   carrot, tomato      erodes steadily
    linear strawberry, milk    on the floor inside ~100 units
    sq     wool, melon         on the floor inside ~60

Any planting decision priced at a product's *current* price will over-plant the
thin markets, because that price is the first unit's price and not the next
one's. This prints both so the difference is visible.

    python lab/depth.py            # the table
    python lab/depth.py 250        # marginal revenue at a chosen volume
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kaggle_environments.envs.kaggriculture.kaggriculture import (  # noqa: E402
    MARKET_I0,
    MARKET_PARAMS,
    market_price,
)


def revenue(item, n, start=MARKET_I0):
    """Total earned selling n units from `start`, walking the price down."""
    total = 0
    inventory = start
    for _ in range(n):
        price = market_price(item, inventory)
        total += price
        if price > 1:  # $1 sales do not add supply
            inventory += 1
    return total


def table(volume=400):
    half = volume // 4
    print(f"{'product':<12}{'shape':>8}{'base':>6}{f'p@{half}':>8}{f'p@{volume}':>8}"
          f"{f'revenue {volume}':>15}{'avg each':>10}{'last each':>11}")
    for item, params in MARKET_PARAMS.items():
        base = market_price(item, MARKET_I0)
        gross = revenue(item, volume)
        prev = revenue(item, volume - 1)
        print(f"{item:<12}{params['above_func']:>8}{base:>6}"
              f"{market_price(item, MARKET_I0 + half):>8}"
              f"{market_price(item, MARKET_I0 + volume):>8}"
              f"{gross:>15,}{gross / volume:>10.0f}{gross - prev:>11}")


if __name__ == "__main__":
    table(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
