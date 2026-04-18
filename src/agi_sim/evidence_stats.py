from __future__ import annotations

import math
import random
from statistics import mean
from typing import Iterable, Sequence

Z_95 = 1.959963984540054


def _clip01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _percentile(sorted_values: Sequence[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if q <= 0.0:
        return float(sorted_values[0])
    if q >= 1.0:
        return float(sorted_values[-1])

    index = q * (len(sorted_values) - 1)
    lo = int(math.floor(index))
    hi = int(math.ceil(index))
    if lo == hi:
        return float(sorted_values[lo])

    weight = index - lo
    return float(sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight)


def wilson_interval(successes: int, total: int, *, z: float = Z_95) -> tuple[float | None, float | None]:
    if total <= 0:
        return (None, None)

    p = float(successes) / float(total)
    denom = 1.0 + ((z * z) / float(total))
    center = p + ((z * z) / (2.0 * float(total)))
    spread = z * math.sqrt((p * (1.0 - p) / float(total)) + ((z * z) / (4.0 * float(total * total))))

    lower = (center - spread) / denom
    upper = (center + spread) / denom
    return (_clip01(lower), _clip01(upper))


def proportion_summary(binary_scores: Sequence[float]) -> dict[str, float | int | None]:
    total = len(binary_scores)
    successes = int(sum(1 for value in binary_scores if value >= 0.5))
    point_estimate = (float(successes) / float(total)) if total > 0 else None
    ci_low, ci_high = wilson_interval(successes, total)

    return {
        "n": total,
        "successes": successes,
        "point_estimate": point_estimate,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    iterations: int = 2000,
    alpha: float = 0.05,
    seed: int = 1337,
) -> tuple[float | None, float | None]:
    if not values:
        return (None, None)

    rng = random.Random(seed)
    n = len(values)
    boot_means: list[float] = []

    for _ in range(max(300, iterations)):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot_means.append(float(mean(sample)))

    boot_means.sort()
    low = _percentile(boot_means, alpha / 2.0)
    high = _percentile(boot_means, 1.0 - (alpha / 2.0))
    return (low, high)


def cohens_h(p1: float, p2: float) -> float:
    # Cohen's h is a scale-free effect size for difference in proportions.
    p1c = _clip01(float(p1))
    p2c = _clip01(float(p2))
    return (2.0 * math.asin(math.sqrt(p1c))) - (2.0 * math.asin(math.sqrt(p2c)))


def mean_or_none(values: Iterable[float]) -> float | None:
    prepared = list(values)
    if not prepared:
        return None
    return float(mean(prepared))


def conservative_delta_ci_from_component_cis(
    candidate_ci_low: float | None,
    candidate_ci_high: float | None,
    baseline_ci_low: float | None,
    baseline_ci_high: float | None,
) -> tuple[float | None, float | None]:
    if (
        candidate_ci_low is None
        or candidate_ci_high is None
        or baseline_ci_low is None
        or baseline_ci_high is None
    ):
        return (None, None)

    return (
        float(candidate_ci_low) - float(baseline_ci_high),
        float(candidate_ci_high) - float(baseline_ci_low),
    )
