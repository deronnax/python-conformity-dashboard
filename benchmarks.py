"""Time classic CPU-bound kernels and standard library workloads.

Run as `python benchmarks.py <name>` on one interpreter. The kernels follow
well-known algorithms (the n-body, fannkuch-redux and spectral-norm programs of
the Computer Language Benchmarks Game, n-queens, a floating-point loop) and
stdlib-heavy work (json, re, collections). Each prints a JSON document with a
checksum of its result, so the dashboard can tell a wrong answer from a slow one.

The first call is reported apart: JIT compilers (PyPy, GraalPy) are slow while
they warm up and fast afterwards, and both facts matter.
"""

import json
import math
import re
import sys
import time
import zlib
from collections import Counter
from itertools import permutations

# Timing budget in seconds. Slow interpreters run fewer rounds instead of
# stretching the whole measurement.
BUDGET = 2.5
HARD_LIMIT = 40
MIN_ROUNDS = 3
MAX_ROUNDS = 15
WARMUP_ROUNDS = 2
WARMUP_ONLY_BELOW = 5  # skip extra warmup when one round is already this slow


def lcg(seed):
    """Deterministic pseudo-random integers, identical on every interpreter."""
    state = seed
    while True:
        state = (state * 1103515245 + 12345) % 2147483648
        # The low bits of a power-of-two LCG repeat with a short period.
        yield state >> 8


# --- n-body: floating-point arithmetic on small lists ---------------------

PI = 3.14159265358979323
SOLAR_MASS = 4 * PI * PI
DAYS = 365.24
BODIES = (
    ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], SOLAR_MASS),
    ([4.84143144246472090e00, -1.16032004402742839e00, -1.03622044471123109e-01],
     [1.66007664274403694e-03 * DAYS, 7.69901118419740425e-03 * DAYS, -6.90460016972063023e-05 * DAYS],
     9.54791938424326609e-04 * SOLAR_MASS),
    ([8.34336671824457987e00, 4.12479856412430479e00, -4.03523417114321381e-01],
     [-2.76742510726862411e-03 * DAYS, 4.99852801234917238e-03 * DAYS, 2.30417297573763929e-05 * DAYS],
     2.85885980666130812e-04 * SOLAR_MASS),
    ([1.28943695621391310e01, -1.51111514016986312e01, -2.23307578892655734e-01],
     [2.96460137564761618e-03 * DAYS, 2.37847173959480950e-03 * DAYS, -2.96589568540237556e-05 * DAYS],
     4.36624404335156298e-05 * SOLAR_MASS),
    ([1.53796971148509165e01, -2.59193146099879641e01, 1.79258772950371181e-01],
     [2.68067772490389322e-03 * DAYS, 1.62824170038242295e-03 * DAYS, -9.51592254519715870e-05 * DAYS],
     5.15138902046611451e-05 * SOLAR_MASS),
)


def energy(bodies):
    total = 0.0
    for index, (position, velocity, mass) in enumerate(bodies):
        total += 0.5 * mass * (velocity[0] ** 2 + velocity[1] ** 2 + velocity[2] ** 2)
        for other_position, _, other_mass in bodies[index + 1:]:
            dx = position[0] - other_position[0]
            dy = position[1] - other_position[1]
            dz = position[2] - other_position[2]
            total -= mass * other_mass / math.sqrt(dx * dx + dy * dy + dz * dz)
    return total


def nbody(steps=50000, step=0.01):
    bodies = [([*position], [*velocity], mass) for position, velocity, mass in BODIES]
    momentum = [0.0, 0.0, 0.0]
    for _, velocity, mass in bodies:
        for axis in range(3):
            momentum[axis] -= velocity[axis] * mass
    bodies[0][1][:] = [value / SOLAR_MASS for value in momentum]
    pairs = [(a, b) for index, a in enumerate(bodies) for b in bodies[index + 1:]]
    for _ in range(steps):
        for (p1, v1, m1), (p2, v2, m2) in pairs:
            dx = p1[0] - p2[0]
            dy = p1[1] - p2[1]
            dz = p1[2] - p2[2]
            squared = dx * dx + dy * dy + dz * dz
            magnitude = step / (squared * math.sqrt(squared))
            v1[0] -= dx * m2 * magnitude
            v1[1] -= dy * m2 * magnitude
            v1[2] -= dz * m2 * magnitude
            v2[0] += dx * m1 * magnitude
            v2[1] += dy * m1 * magnitude
            v2[2] += dz * m1 * magnitude
        for position, velocity, _ in bodies:
            position[0] += step * velocity[0]
            position[1] += step * velocity[1]
            position[2] += step * velocity[2]
    return f"{energy(bodies):.9f}"


# --- fannkuch-redux: integer permutations on lists ------------------------

def fannkuch(n=8, repeat=4):
    for _ in range(repeat - 1):
        fannkuch_once(n)
    return fannkuch_once(n)


def fannkuch_once(n):
    count = list(range(n))
    permutation = list(range(n))
    maximum = checksum = sign_index = 0
    r = n
    while True:
        while r != 1:
            count[r - 1] = r
            r -= 1
        flipped = permutation[:]
        flips = 0
        while flipped[0]:
            head = flipped[0]
            flipped[: head + 1] = flipped[head::-1]
            flips += 1
        maximum = max(maximum, flips)
        checksum += flips if sign_index % 2 == 0 else -flips
        while True:
            if r == n:
                return f"{checksum} {maximum}"
            first = permutation[0]
            for position in range(r):
                permutation[position] = permutation[position + 1]
            permutation[r] = first
            count[r] -= 1
            if count[r] > 0:
                break
            r += 1
        sign_index += 1


# --- spectral norm: nested loops and generator expressions ----------------

def spectral_norm(size=200):
    def element(i, j):
        return 1.0 / ((i + j) * (i + j + 1) // 2 + i + 1)

    def times(vector):
        return [sum(element(i, j) * value for j, value in enumerate(vector)) for i in range(size)]

    def times_transpose(vector):
        return [sum(element(j, i) * value for j, value in enumerate(vector)) for i in range(size)]

    u = [1.0] * size
    for _ in range(10):
        v = times_transpose(times(u))
        u = times_transpose(times(v))
    vbv = sum(a * b for a, b in zip(u, v))
    vv = sum(b * b for b in v)
    return f"{math.sqrt(vbv / vv):.9f}"


# --- n-queens: permutations and set construction --------------------------

def queens(size=9):
    columns = range(size)
    solutions = 0
    for vector in permutations(columns):
        if size == len({vector[i] + i for i in columns}) == len({vector[i] - i for i in columns}):
            solutions += 1
    return str(solutions)


# --- float: attribute access and math functions on many small objects -----

class Point:
    __slots__ = ("x", "y", "z")

    def __init__(self, i):
        self.x = x = math.sin(i)
        self.y = math.cos(i) * 3
        self.z = (x * x) / 2

    def normalize(self):
        norm = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        self.x /= norm
        self.y /= norm
        self.z /= norm

    def maximize(self, other):
        self.x = self.x if self.x > other.x else other.x
        self.y = self.y if self.y > other.y else other.y
        self.z = self.z if self.z > other.z else other.z
        return self


def float_points(count=400000):
    points = [Point(i) for i in range(count)]
    for point in points:
        point.normalize()
    best = points[0]
    for point in points[1:]:
        best = best.maximize(point)
    return f"{best.x:.9f} {best.y:.9f} {best.z:.9f}"


# --- json: encoder and decoder on nested documents ------------------------

def json_roundtrip(documents=1500):
    numbers = lcg(7)
    data = [
        {
            "id": index,
            "name": f"item-{next(numbers) % 1000}",
            "tags": [f"t{next(numbers) % 50}" for _ in range(5)],
            "price": (next(numbers) % 100000) / 100,
            "nested": {"flag": index % 2 == 0, "values": [next(numbers) % 1000 for _ in range(10)], "note": None},
        }
        for index in range(documents)
    ]
    total = 0
    for _ in range(20):
        text = json.dumps(data, sort_keys=True)
        assert json.loads(text) == data
        total += zlib.crc32(text.encode("utf-8"))
    return f"{len(text)} {total}"


# --- regex: compiled patterns over generated text -------------------------

def regex_search(words=120000):
    numbers = lcg(11)
    pieces = []
    for _ in range(words):
        value = next(numbers)
        kind = value % 4
        if kind == 0:
            pieces.append(f"user{value % 97}@host{value % 13}.com")
        elif kind == 1:
            pieces.append(f"{100 + value % 900}-{1000 + value % 9000}")
        elif kind == 2:
            pieces.append("queue" * (1 + value % 2) + str(value % 10))
        else:
            pieces.append("lorem")
    text = " ".join(pieces)
    patterns = (r"\b\w+@\w+\.com\b", r"(\d{3})-(\d{4})", r"[aeiou]{2,}", r"(?i)\bQUEUE\d\b")
    counts = [len(re.findall(pattern, text)) for pattern in patterns]
    counts.append(len(re.sub(r"\d+", "#", text)))
    return " ".join(map(str, counts))


# --- word count: dict, Counter and sorting on strings ---------------------

def word_count(words=500000):
    numbers = lcg(3)
    vocabulary = [f"w{n % 2000}" for n in (next(numbers) for _ in range(2000))]
    text = " ".join(vocabulary[next(numbers) % len(vocabulary)] for _ in range(words))
    counts = Counter(text.split())
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return " ".join(f"{word}:{count}" for word, count in ranked[:5])


BENCHMARKS = {
    "nbody": (nbody, "N-body simulation", "Simulation à N corps"),
    "fannkuch": (fannkuch, "Fannkuch-redux permutations", "Permutations fannkuch-redux"),
    "spectral-norm": (spectral_norm, "Spectral norm", "Norme spectrale"),
    "nqueens": (queens, "N-queens with permutations", "N reines par permutations"),
    "float": (float_points, "Floating-point objects", "Objets à virgule flottante"),
    "json": (json_roundtrip, "JSON encode and decode", "Encodage et décodage JSON"),
    "regex": (regex_search, "Regular expression search", "Recherche par expressions régulières"),
    "word-count": (word_count, "Word frequency count", "Comptage de fréquence des mots"),
}


def timed(function):
    start = time.perf_counter()
    value = function()
    return time.perf_counter() - start, value


def measure(function):
    first, value = timed(function)
    for _ in range(WARMUP_ROUNDS if first < WARMUP_ONLY_BELOW else 0):
        timed(function)
    samples = []
    started = time.perf_counter()
    while len(samples) < MAX_ROUNDS:
        elapsed = time.perf_counter() - started
        if len(samples) >= MIN_ROUNDS and elapsed >= BUDGET:
            break
        if samples and elapsed >= HARD_LIMIT:
            break
        duration, again = timed(function)
        if again != value:
            raise RuntimeError(f"Unstable result: {value!r} then {again!r}")
        samples.append(duration)
    return {"result": value, "first": round(first, 5), "samples": [round(item, 5) for item in samples]}


if __name__ == "__main__":
    print(json.dumps(measure(BENCHMARKS[sys.argv[1]][0])))
