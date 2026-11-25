"""Relative speed of each interpreter against the CPython reference."""

from math import exp, log
from statistics import median, stdev


def summarize(samples):
    """Statistics of timed rounds in seconds."""
    return {
        "median": round(median(samples), 5),
        "min": round(min(samples), 5),
        "stdev": round(stdev(samples), 5) if len(samples) > 1 else 0.0,
        "rounds": len(samples),
    }


def speedup(row, runtime):
    """How many times faster than CPython a benchmark ran, or None when either side was not measured."""
    reference = row["outcomes"].get("cpython", {})
    outcome = row["outcomes"].get(runtime, {})
    if reference.get("status") != "passed" or outcome.get("status") != "passed":
        return None
    return reference["median"] / outcome["median"]


def geometric_means(rows, runtimes):
    """Return {runtime id: (geometric mean speedup, benchmarks counted)}."""
    means = {}
    for runtime in runtimes:
        values = [value for row in rows if (value := speedup(row, runtime)) is not None]
        if values:
            means[runtime] = (exp(sum(map(log, values)) / len(values)), len(values))
    return means
