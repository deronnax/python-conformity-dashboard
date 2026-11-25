"""Measure whether Python threads execute bytecode in parallel.

Four threads run the same CPU-bound function. The speedup compares them with
running the four calls one after another: about 1 means the threads take turns
(a global lock), close to the number of workers means they run in parallel.
"""

import json
import os
import sys
import threading
import time

WORKERS = 4
TARGET = 0.25
LIMIT = 200_000_000
ROUNDS = 3


def spin(count):
    total = 0
    for number in range(count):
        total += number * number % 7
    return total


def timed(function):
    start = time.perf_counter()
    function()
    return time.perf_counter() - start


def cores():
    if hasattr(os, "sched_getaffinity"):
        return len(os.sched_getaffinity(0))
    return os.cpu_count() or 1


def main():
    # Doubling until a call lasts long enough also warms up JIT compilers.
    count = 20_000
    while timed(lambda: spin(count)) < TARGET and count < LIMIT:
        count *= 2
    spin(count)

    def sequential():
        for _ in range(WORKERS):
            spin(count)

    def parallel():
        threads = [threading.Thread(target=spin, args=(count,)) for _ in range(WORKERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    one_after_another = min(timed(sequential) for _ in range(ROUNDS))
    together = min(timed(parallel) for _ in range(ROUNDS))
    gil = getattr(sys, "_is_gil_enabled", None)
    print(json.dumps({
        "workers": WORKERS,
        "cores": cores(),
        "sequential": round(one_after_another, 3),
        "parallel": round(together, 3),
        "speedup": round(one_after_another / together, 2),
        "gil": gil() if gil else None,
    }))


if __name__ == "__main__":
    main()
