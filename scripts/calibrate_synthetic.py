"""Find UPHOLD_SCALE and REDUCED_SHARE so that simulated outcomes match the official 2020 court outcomes."""
from __future__ import annotations

import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_synthetic as g  # noqa: E402

TARGET = {"maintenu": 0.515, "reduit": 0.339, "annule": 0.145}


def rates(scale: float, share: float, n: int = 1500) -> dict:
    g.UPHOLD_SCALE, g.REDUCED_SHARE = scale, share
    rng = random.Random(7)
    counts = Counter()
    for i in range(n):
        nd = g.rand_date(rng, date(2020, 1, 1), date(2025, 6, 30))
        notif = g.make_notification(rng, f"C-{i}", nd)
        for issue in g.simulate_outcome(rng, notif, round(rng.betavariate(2, 2.5), 2), rng.random() < 0.82):
            counts[issue.issue] += 1
    total = sum(counts.values())
    return {k: counts[k] / total for k in TARGET}


best = None
for scale in [x / 10 for x in range(10, 26)]:
    for share in [x / 100 for x in range(40, 91, 5)]:
        r = rates(scale, share)
        err = sum((r[k] - TARGET[k]) ** 2 for k in TARGET)
        if best is None or err < best[0]:
            best = (err, scale, share, r)
print("UPHOLD_SCALE =", best[1], "REDUCED_SHARE =", best[2], {k: round(v, 3) for k, v in best[3].items()})
