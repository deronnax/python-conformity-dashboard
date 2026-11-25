"""Measure public Python API behavior and generate the static dashboard."""

import argparse
import ast
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent, indent
from urllib.request import urlretrieve

from applications import application_results
from benchmarks import BENCHMARKS
from corpus import CPYTHON_VERSION, PROBES, UPSTREAM, source_url
from dashboard import generate
from history import load as load_history
from package_bench import package_results
from performance import summarize


ROOT = Path(__file__).resolve().parent
ARCHIVE = f"Python-{CPYTHON_VERSION}.tar.xz"
ARCHIVE_URL = f"https://www.python.org/ftp/python/{CPYTHON_VERSION}/{ARCHIVE}"
ARCHIVE_SHA256 = "c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a"
RUNTIME_NAMES = {"cpython": "CPython", "pypy": "PyPy", "graalpy": "GraalPy", "rustpython": "RustPython",
                 "freethreaded": "CPython 3.14t"}
# Measured for speed and thread scaling only: RustPython has no C API, so it cannot
# run extension modules and the conformity suites would mostly measure that.
PERFORMANCE_ONLY = {"rustpython"}
# Interpreters that run the CPython tests: the ones targeting the same Python version.
UPSTREAM_RUNTIMES = ("cpython", "pypy", "graalpy")
# sys.implementation.name reported by each runtime id.
IMPLEMENTATIONS = {"freethreaded": "cpython"}


def run(executable, *args, cwd, timeout=30):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "RUSTPYTHON"))}
    return subprocess.run([executable, "-I", "-S", "-B", *args], cwd=cwd, env=env, timeout=timeout,
                          capture_output=True, encoding="utf-8", errors="replace")


# Reports the language version apart from the implementation version: PyPy 8.0.1
# implements Python 3.12.15, for example.
DESCRIBE = """
import json, sys
def version(info):
    text = ".".join(str(part) for part in tuple(info)[:3])
    level = getattr(info, "releaselevel", "final")
    if level != "final":
        text += {"alpha": "a", "beta": "b", "candidate": "rc"}.get(level, level) + str(getattr(info, "serial", ""))
    return text
print(json.dumps({"implementation": sys.implementation.name,
                  "implementationVersion": version(sys.implementation.version),
                  "language": version(sys.version_info), "version": sys.version,
                  "cacheTag": sys.implementation.cache_tag}))
"""


def language_mismatch(language, reference=CPYTHON_VERSION):
    """True when an interpreter implements another minor version than the reference."""
    return language.split(".")[:2] != reference.split(".")[:2]


def identify(executable, runtime, cwd):
    info = run(executable, "-c", DESCRIBE, cwd=cwd)
    try:
        described = json.loads(info.stdout)
    except ValueError:
        described = {}
    name, version = described.get("implementation"), described.get("version")
    if info.returncode or name != IMPLEMENTATIONS.get(runtime, runtime) or not version:
        raise ValueError(f"{executable} is not {RUNTIME_NAMES[runtime]}. {info.stderr.strip()}")
    if runtime in ("cpython", "pypy") and version.split()[0] != CPYTHON_VERSION:
        raise ValueError(f"{RUNTIME_NAMES[runtime]} must target Python {CPYTHON_VERSION}, got {version.split()[0]}.")
    if runtime == "graalpy" and version.split()[0].rpartition(".")[0] != CPYTHON_VERSION.rpartition(".")[0]:
        raise ValueError(f"GraalPy must target Python {CPYTHON_VERSION.rpartition('.')[0]}, got {version.split()[0]}.")
    if runtime == "freethreaded" and "free-threading build" not in version:
        raise ValueError(f"{executable} is not a free-threaded CPython build.")
    return {"id": runtime, "name": RUNTIME_NAMES[runtime], "version": version,
            "implementation": name, "implementationVersion": described["implementationVersion"],
            "language": described["language"], "cacheTag": described.get("cacheTag"),
            "crossVersion": language_mismatch(described["language"])}


def extract_tests(archive, directory):
    if not archive:
        archive = directory / ARCHIVE
        urlretrieve(ARCHIVE_URL, archive)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != ARCHIVE_SHA256:
        raise ValueError(f"The digest of {archive} does not match the official archive.")
    test_path = f"Python-{CPYTHON_VERSION}/Lib/test"
    with tarfile.open(archive) as source:
        members = [item for item in source.getmembers() if item.name.startswith(test_path + "/")]
        source.extractall(directory, members, filter="data")
    # The package initializer sets up a CPython-only backend even when the
    # selected tests only need PyTest. CTest already skips an absent backend.
    json_fixture = directory / test_path / "test_json" / "__init__.py"
    fixture_source = json_fixture.read_text(encoding="utf-8")
    accelerator_setup = "cjson.JSONDecodeError = cjson.decoder.JSONDecodeError = json.JSONDecodeError"
    if fixture_source.count(accelerator_setup) != 1:
        raise ValueError("Initialisation inattendue du harnais JSON.")
    fixture_source = fixture_source.replace(accelerator_setup, "if cjson is not None:\n    " + accelerator_setup)
    json_fixture.write_text(fixture_source, encoding="utf-8")
    # Keep the other contents of CPython's Lib off the target's import path.
    return directory / test_path


def result(status, detail="", *, detail_fr=None):
    outcome = {"status": status, "detail": detail}
    if detail_fr is not None:
        outcome["detailFr"] = detail_fr
    return outcome


# Text that only appears when the interpreter itself fails, below the Python level.
INTERNAL_FAILURES = ("java.lang.", "com.oracle.truffle.", "Fatal Python error", "RPython traceback",
                     "panicked at")


def internal_failure(text):
    return any(marker in text for marker in INTERNAL_FAILURES)


def invoke(executable, *args, cwd, timeout=30):
    try:
        completed = run(executable, *args, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        return result("timeout", f"The process exceeded {timeout} seconds.",
                      detail_fr=f"Le processus a dépassé {timeout} secondes.")
    except OSError as exc:
        return result("blocked", str(exc))
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        # A host exception or a fatal error is a failure of the interpreter, not of the
        # measurement. Any other exit stays blocked: the cause is unknown.
        if completed.returncode < 0:
            status = "crash"
        elif internal_failure(detail):
            status = "internalError"
        else:
            status = "blocked"
        if detail:
            return result(status, detail)
        return result(status, f"Exit code {completed.returncode}", detail_fr=f"Code de sortie {completed.returncode}")
    return completed.stdout.strip()


def observe(executable, probe, cwd):
    module, *attributes = probe.api.split(".")
    expected_exception = ""
    exception_type = "None"
    if probe.expected.startswith("exception: "):
        expected_exception = probe.expected.removeprefix("exception: ")
        owner, _, name = expected_exception.rpartition(".")
        namespace = "module" if owner else "__import__('builtins')"
        exception_type = f"getattr({namespace}, {name!r}, None)"
    preparation = indent(dedent(probe.setup).strip(), "            ")
    code = f"""
try:
    module = __import__({module!r})
except ImportError as exc:
    print('missing', {module!r}, str(exc))
else:
    try:
        api = module
        for attribute in {attributes!r}:
            api = getattr(api, attribute)
    except AttributeError:
        print('missing', {probe.api!r})
    else:
        try:
{preparation}
            value = {probe.expression}
        except Exception as exc:
            expected = {exception_type}
            if expected is not None and isinstance(exc, expected):
                print('exception', {expected_exception!r})
            else:
                print('unexpected-exception', type(exc).__name__)
        else:
            print('value', type(value).__name__, repr(value))
"""
    output = invoke(executable, "-c", code, cwd=cwd)
    if isinstance(output, dict):
        return output
    kind, _, payload = output.partition(" ")
    if kind in ("missing", "blocked"):
        return result(kind, payload)
    if kind == "exception":
        return f"exception: {payload}"
    if kind == "unexpected-exception":
        return f"unexpected exception: {payload}"
    if kind == "value":
        value_type, _, value = payload.partition(" ")
        try:
            return f"{value_type}: {ast.literal_eval(value)!r}"
        except (ValueError, SyntaxError):
            pass
    return result("blocked", f"Unreadable process output: {output}", detail_fr=f"Sortie illisible du processus : {output}")


def french_observation(observation):
    if observation.startswith("unexpected exception: "):
        return observation.replace("unexpected exception: ", "exception inattendue : ", 1)
    return observation


def comparisons(executables, cwd, lib=None):
    rows = []
    for probe in PROBES:
        baseline = observe(executables["cpython"], probe, cwd)
        outcomes = {}
        for runtime, executable in executables.items():
            observation = baseline if runtime == "cpython" else observe(executable, probe, cwd)
            if isinstance(observation, dict):
                outcome = observation
            elif baseline != probe.expected:
                status = "blocked" if runtime == "cpython" else "unverified"
                outcome = result(status, f"Expected by the corpus: {probe.expected}\nObserved: {observation}",
                                 detail_fr=f"Attendu dans le corpus : {probe.expected}\nObservé : {french_observation(observation)}")
            else:
                translated = french_observation(observation)
                outcome = result("passed" if observation == baseline else "different", observation,
                                 detail_fr=translated if translated != observation else None)
            outcomes[runtime] = outcome
        snippet = "\n".join(part for part in (dedent(probe.setup).strip(), probe.expression) if part)
        snippet = snippet.replace("api(", probe.api + "(").replace("module.", probe.module + ".")
        rows.append({"id": probe.id, "module": probe.module, "api": probe.api, "title": probe.title,
                     "titleFr": probe.title_fr, "contract": probe.contract, "contractSource": probe.contract_source,
                     "code": f"import {probe.module}\n\n{snippet}", "source": source_url(probe.upstream, lib),
                     "sourceTest": probe.upstream, "outcomes": outcomes})
    return rows


def thread_results(executables, cwd):
    """Measure CPU-bound thread scaling. A failed measurement keeps its status instead of a speedup."""
    measured = {}
    for runtime, executable in executables.items():
        observation = invoke(executable, str(ROOT / "threads.py"), cwd=cwd, timeout=120)
        try:
            measured[runtime] = observation if isinstance(observation, dict) else json.loads(observation)
        except ValueError:
            measured[runtime] = result("blocked", observation)
    return measured


def benchmark_results(executables, cwd):
    """Time each benchmark in its own process and check its answer against CPython's."""
    rows = []
    for name, (_, title, title_fr) in BENCHMARKS.items():
        measured = {}
        for runtime, executable in executables.items():
            observation = invoke(executable, str(ROOT / "benchmarks.py"), name, cwd=cwd, timeout=240)
            try:
                measured[runtime] = observation if isinstance(observation, dict) else json.loads(observation)
            except ValueError:
                measured[runtime] = result("blocked", observation)
        expected = measured["cpython"].get("result")
        outcomes = {}
        for runtime, observed in measured.items():
            if "samples" not in observed:
                outcomes[runtime] = observed
            elif expected is None:
                outcomes[runtime] = result("unverified", f"The CPython reference did not finish.\nObserved: {observed['result']}",
                                           detail_fr=f"La référence CPython n’a pas terminé.\nObservé : {observed['result']}")
            elif observed["result"] != expected:
                outcomes[runtime] = result("different", f"Expected: {expected}\nObserved: {observed['result']}",
                                           detail_fr=f"Attendu : {expected}\nObservé : {observed['result']}")
            else:
                outcomes[runtime] = {"status": "passed", "detail": "", "first": observed["first"],
                                     **summarize(observed["samples"])}
        rows.append({"id": name, "title": title, "titleFr": title_fr, "outcomes": outcomes})
    return rows


def upstream_results(executables, tests, cwd):
    """Run the selected CPython test methods on the interpreters that target the same Python version."""
    runtimes = [runtime for runtime in UPSTREAM_RUNTIMES if runtime in executables]
    rows = []
    for module, methods in UPSTREAM.items():
        for method in methods:
            outcomes = {}
            for runtime in runtimes:
                observation = invoke(executables[runtime], str(ROOT / "upstream.py"),
                                     str(tests.parent), method, cwd=cwd)
                try:
                    outcomes[runtime] = observation if isinstance(observation, dict) else json.loads(observation)
                except ValueError:
                    outcomes[runtime] = result("blocked", observation)
            if outcomes["cpython"]["status"] != "passed":
                for runtime in runtimes[1:]:
                    observed = outcomes[runtime]
                    outcomes[runtime] = result("unverified", f"Observed status: {observed['status']}\n{observed['detail']}",
                                               detail_fr=f"État observé : {observed['status']}\n{observed.get('detailFr', observed['detail'])}")
            rows.append({"id": method, "module": module, "title": method.split(".")[-1],
                         "source": source_url(method, tests.parent), "sourceTest": method, "outcomes": outcomes})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpython", default=sys.executable, help=f"Reference binary, Python {CPYTHON_VERSION}")
    parser.add_argument("--pypy", default="pypy3.12", help=f"PyPy binary targeting Python {CPYTHON_VERSION}")
    parser.add_argument("--graalpy", help="Standalone GraalPy binary. Added to the shared cases when given.")
    parser.add_argument("--rustpython", help="RustPython binary. Measured for performance and threads only.")
    parser.add_argument("--freethreaded", help="Free-threaded CPython 3.14 binary. Added to the shared cases when given.")
    parser.add_argument("--history", type=Path, help="history.json from an earlier run, extended by this one")
    parser.add_argument("--benchmarks", action="store_true", help="Time compute kernels and standard library workloads")
    parser.add_argument("--applications", action="store_true", help="Run Django, Bottle and NumPy scenarios in a temporary directory")
    parser.add_argument("--packages", action="store_true", help="Install and import the 50 most downloaded PyPI projects")
    parser.add_argument("--source", type=Path, help=f"Official {ARCHIVE} archive, downloaded when omitted")
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="Directory of the generated site")
    args = parser.parse_args()

    try:
        executables = {}
        for runtime in RUNTIME_NAMES:
            command = getattr(args, runtime)
            if command:
                path = shutil.which(command)
                if not path:
                    raise ValueError(f"Binary not found: {command}")
                executables[runtime] = os.path.abspath(path)

        with tempfile.TemporaryDirectory(prefix="python-conformity-") as temp:
            directory = Path(temp)
            runtimes = [identify(path, runtime, directory) for runtime, path in executables.items()]
            for runtime, threads in thread_results(executables, directory).items():
                next(item for item in runtimes if item["id"] == runtime)["threads"] = threads
            benchmarks = benchmark_results(executables, directory) if args.benchmarks else []
            tests = extract_tests(args.source, directory)
            conformity = {runtime: path for runtime, path in executables.items() if runtime not in PERFORMANCE_ONLY}
            report = {
                "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "platform": f"{platform.system()} {platform.release()} · {platform.machine()}",
                "reference": CPYTHON_VERSION,
                "runtimes": runtimes,
                "common": comparisons(conformity, directory, tests.parent),
                "upstream": upstream_results(conformity, tests, directory),
                "benchmarks": benchmarks,
                "applications": application_results(conformity, directory, invoke) if args.applications else [],
                "packages": package_results(conformity, directory) if args.packages else None,
            }
            generate(report, args.output, load_history(args.history) if args.history else [])
    except (OSError, ValueError, subprocess.TimeoutExpired, tarfile.TarError) as exc:
        parser.exit(1, f"Measurement aborted: {exc}\n")

    print(f"{len(report['common'])} shared cases · {len(report['upstream'])} upstream tests · {args.output / 'index.html'}")
    for suite in ("common", "upstream", "applications"):
        for runtime in executables:
            outcomes = [row["outcomes"][runtime]["status"] for row in report[suite] if runtime in row["outcomes"]]
            if outcomes:
                print(f"{suite} / {runtime}: {outcomes.count('passed')}/{len(outcomes)} passed")
    if report["packages"]:
        for runtime in report["packages"]["items"][0]["outcomes"]:
            counts = {}
            for package in report["packages"]["items"]:
                status = package["outcomes"][runtime]["status"]
                counts[status] = counts.get(status, 0) + 1
            print(f"packages / {runtime}: {counts}")
    return int(any(row["outcomes"]["cpython"]["status"] != "passed"
                   for suite in ("common", "upstream") for row in report[suite]))


if __name__ == "__main__":
    sys.exit(main())
