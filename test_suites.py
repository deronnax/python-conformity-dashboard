"""Run the test suite of a large project on one interpreter, then compare interpreters.

Django's own test suite runs with SQLite and only the packages Django requires,
so tests that need an optional package are skipped everywhere. Every test outcome
is recorded as the run goes, which keeps the results of a run that times out.

    python3 fetch.py 3.11 pypy
    python3 test_suites.py --version 3.11 --runtime pypy --output suite.json

The dashboard compares each interpreter with CPython: the tests that pass on
CPython and fail on the interpreter, grouped by Django app and error message.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from applications import DJANGO, PYPI, Wheel, prepare
from fetch import executable as downloaded, fetch
from references import REFERENCES, Archive

PROJECT, VERSION = "Django", "5.2.19"
SOURCE = Archive(PYPI + "source/d/django/django-5.2.19.tar.gz",
                 "ad03d8abc51dbff95ebf34b27123cf0c26a3b62db7ba0cd520783686362533d1")
# Django itself comes from the source tree; asgiref and sqlparse are its requirements.
# tblib lets the parallel runner send tracebacks back to the main process.
DEPENDENCIES = DJANGO[1:] + (
    Wheel(PYPI + "02/be/5d2d47b1fb58943194fb59dcf222f7c4e35122ec0ffe8c36e18b5d728f0b/tblib-3.2.2-py3-none-any.whl",
          "26bdccf339bcce6a88b2b5432c988b266ebbe63a4e593f6b578b1d2e723d2b76"),
)
TIMEOUT = 70 * 60

SETTINGS = '''from test_sqlite import *  # noqa: F403

TEST_RUNNER = "conformity_runner.RecordingRunner"
'''
RUNNER = '''import json
import os
import unittest

from django.test.runner import DiscoverRunner


class RecordingResult(unittest.TextTestResult):
    """Write one JSON line per outcome, as the main process receives it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record = open(os.environ["CONFORMITY_RESULTS"], "a", encoding="utf-8", buffering=1)

    def write(self, test, status, err=None):
        entry = {"id": test.id(), "status": status}
        if err is not None:
            lines = self._exc_info_to_string(err, test).strip().splitlines()
            entry["traceback"] = "\\n".join(lines[-15:])
        self.record.write(json.dumps(entry) + "\\n")

    def addSuccess(self, test):
        super().addSuccess(test)
        self.write(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.write(test, "failure", err)

    def addError(self, test, err):
        super().addError(test, err)
        self.write(test, "error", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.write(test, "skipped")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.write(test, "expectedFailure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.write(test, "unexpectedSuccess")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            failed = issubclass(err[0], test.failureException)
            self.write(test, "failure" if failed else "error", err)


class RecordingRunner(DiscoverRunner):
    def get_resultclass(self):
        return RecordingResult
'''
# runtests.py runs through this launcher. Django runs tests in parallel only when
# processes start with fork or spawn, and Python 3.14 starts them with forkserver on
# Linux. runtests.py also tunes the garbage collector with gc.set_threshold, which
# GraalPy lacks: a no-op stands in, and the page says so. The code of runtests.py
# runs in this module, also in processes started with spawn, which import it again.
LAUNCHER = '''import gc
import multiprocessing
import os

if not hasattr(gc, "set_threshold"):
    gc.set_threshold = lambda *thresholds: None
if __name__ == "__main__" and multiprocessing.get_start_method() == "forkserver":
    multiprocessing.set_start_method("fork", force=True)
__file__ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtests.py")
with open(__file__, encoding="utf-8") as source:
    exec(compile(source.read(), __file__, "exec"))
'''
NO_GC_THRESHOLD = "This interpreter has no gc.set_threshold, which runtests.py calls: the run replaces it with a no-op."
# A test can report several outcomes, such as one per failing subtest: the most
# severe one is kept.
SEVERITY = {"error": 4, "failure": 3, "unexpectedSuccess": 2, "passed": 1, "skipped": 0, "expectedFailure": 0}


def prepare_source(directory):
    """Django's source tree with its dependencies at the root. Django's own tests put
    that root on the PYTHONPATH of the subprocesses they start."""
    source = directory / "django"
    fetch(SOURCE, source)
    dependencies = prepare(DEPENDENCIES, directory / "dependencies")
    for entry in dependencies.iterdir():
        shutil.move(entry, source / entry.name)
    tests = source / "tests"
    (tests / "conformity_settings.py").write_text(SETTINGS, encoding="utf-8")
    (tests / "conformity_runner.py").write_text(RUNNER, encoding="utf-8")
    (tests / "conformity_launcher.py").write_text(LAUNCHER, encoding="utf-8")
    return source


def read_outcomes(path):
    tests, tracebacks = {}, {}
    if not path.exists():
        return tests, tracebacks
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        identifier, status = entry["id"], entry["status"]
        if identifier not in tests or SEVERITY[status] > SEVERITY[tests[identifier]]:
            tests[identifier] = status
            if "traceback" in entry:
                tracebacks[identifier] = entry["traceback"]
    return tests, tracebacks


def run(runtime, executable, directory, labels=(), timeout=TIMEOUT):
    source = prepare_source(directory)
    results = directory / "results.jsonl"
    inherited = ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
    environment = {key: os.environ[key] for key in inherited if key in os.environ}
    environment.update(PYTHONPATH=str(source), CONFORMITY_RESULTS=str(results))
    probe = subprocess.run([executable, "-c", "import gc; print(hasattr(gc, 'set_threshold'))"],
                           capture_output=True, text=True, env=environment, timeout=300)
    note = NO_GC_THRESHOLD if probe.stdout.strip() == "False" else ""
    command = [executable, "conformity_launcher.py", "--settings=conformity_settings", "--parallel=auto",
               "--noinput", *labels]
    started = time.monotonic()
    # A session of its own, so a timeout also stops the worker processes.
    process = subprocess.Popen(command, cwd=source / "tests", env=environment, start_new_session=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    try:
        output, _ = process.communicate(timeout=timeout)
        status = "crash" if process.returncode < 0 else "completed"
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        status = "timeout"
    duration = round(time.monotonic() - started)
    tests, tracebacks = read_outcomes(results)
    tracebacks = {test: text.replace(str(source), "<django>") for test, text in tracebacks.items()}
    if status == "completed" and not tests:
        status = "blocked"
    tail = "\n".join(output.strip().splitlines()[-30:]) if status != "completed" else ""
    return {"suite": "django", "project": PROJECT, "version": VERSION, "runtime": runtime, "status": status,
            "duration": duration, "detail": tail, "note": note, "tests": tests, "tracebacks": tracebacks}


# The comparison keeps a page of a reasonable size: the largest groups, each with
# a few example tests and one traceback.
FAILING = {"failure", "error", "unexpectedSuccess"}
GROUP_LIMIT = 60


def app(test_id):
    """The Django app of a test id, also for errors in setUpClass (module.Class)."""
    match = re.search(r"\(([\w.]+)\)", test_id)
    return (match[1] if match else test_id).split(".")[0]


def message(traceback):
    lines = [line.strip() for line in traceback.strip().splitlines() if line.strip()]
    text = lines[-1] if lines else ""
    return re.sub(r"0x[0-9a-f]+", "0x…", text)[:200]


def group(identifiers, raw):
    groups = defaultdict(list)
    for identifier in sorted(identifiers):
        traceback = raw["tracebacks"].get(identifier, "")
        groups[(app(identifier), raw["tests"][identifier], message(traceback))].append(identifier)
    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    shown = [{"app": name, "status": status, "message": text, "count": len(tests), "examples": tests[:3],
              "traceback": raw["tracebacks"].get(tests[0], "")}
             for (name, status, text), tests in ordered[:GROUP_LIMIT]]
    hidden = ordered[GROUP_LIMIT:]
    return {"groups": shown, "hiddenGroups": len(hidden), "hiddenTests": sum(len(tests) for _, tests in hidden)}


def summarize(raws):
    """Compare the runs of one suite. raws maps a runtime id to the output of run()."""
    baseline = raws.get("cpython")
    reference = baseline["tests"] if baseline and baseline["status"] == "completed" else None
    outcomes = {}
    for runtime, raw in raws.items():
        tests = raw["tests"]
        outcome = {"status": raw["status"], "duration": raw["duration"], "detail": raw["detail"],
                   "note": raw.get("note", ""), "counts": dict(Counter(tests.values()))}
        if runtime == "cpython":
            # Tests that fail on CPython too depend on the environment, not on the interpreter.
            outcome.update(group([test for test, status in tests.items() if status in FAILING], raw))
        elif reference is not None:
            passing = {test for test, status in reference.items() if status == "passed"}
            differing = [test for test in passing if tests.get(test) in FAILING]
            outcome["differences"] = len(differing)
            outcome["notRun"] = len(passing - tests.keys())
            outcome.update(group(differing, raw))
        outcomes[runtime] = outcome
    first = next(iter(raws.values()))
    total = len(reference) if reference is not None else max(len(raw["tests"]) for raw in raws.values())
    return {"id": first["suite"], "project": first["project"], "version": first["version"],
            "tests": total, "outcomes": outcomes}


def load(directory, minor):
    """The suite runs of one Python version, from files named suite-<version>-<runtime>/suite.json."""
    raws = {}
    for path in sorted(Path(directory).glob(f"suite-{minor}-*/suite.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        raws[raw["runtime"]] = raw
    return [summarize(raws)] if raws else []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", choices=REFERENCES, required=True)
    parser.add_argument("--runtime", required=True, help="Interpreter id, such as cpython or pypy")
    parser.add_argument("--executable", type=Path, help="Defaults to the interpreter fetch.py downloaded")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("labels", nargs="*", help="Django test labels, to run part of the suite")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="django-suite-") as temporary:
        executable = arguments.executable or downloaded(arguments.runtime, arguments.version)
        raw = run(arguments.runtime, str(executable.resolve()), Path(temporary), arguments.labels)
    raw["python"] = arguments.version
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(raw), encoding="utf-8")
    counts = Counter(raw["tests"].values())
    print(f"{arguments.runtime}: {raw['status']} in {raw['duration']} s, {dict(counts)}")


if __name__ == "__main__":
    main()
