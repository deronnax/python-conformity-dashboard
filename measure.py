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
from corpus import CPYTHON_VERSION, PROBES, UPSTREAM, source_url
from dashboard import generate


ROOT = Path(__file__).resolve().parent
ARCHIVE = f"Python-{CPYTHON_VERSION}.tar.xz"
ARCHIVE_URL = f"https://www.python.org/ftp/python/{CPYTHON_VERSION}/{ARCHIVE}"
ARCHIVE_SHA256 = "bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599"
RUNTIME_NAMES = {"cpython": "CPython", "pypy": "PyPy", "graalpy": "GraalPy", "rustpython": "RustPython"}


def run(executable, *args, cwd):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("PYTHON", "RUSTPYTHON"))}
    return subprocess.run([executable, "-I", "-S", "-B", *args], cwd=cwd, env=env, timeout=30,
                          capture_output=True, encoding="utf-8", errors="replace")


def identify(executable, runtime, cwd):
    info = run(executable, "-c", "import sys; print(sys.implementation.name); print(sys.version)", cwd=cwd)
    name, _, version = info.stdout.strip().partition("\n")
    if info.returncode or name != runtime or not version:
        raise ValueError(f"{executable} ne correspond pas à {RUNTIME_NAMES[runtime]}. {info.stderr.strip()}")
    if runtime in ("cpython", "pypy") and version.split()[0] != CPYTHON_VERSION:
        raise ValueError(f"{RUNTIME_NAMES[runtime]} doit cibler Python {CPYTHON_VERSION}, reçu {version.split()[0]}.")
    return {"id": runtime, "name": RUNTIME_NAMES[runtime], "version": version}


def extract_tests(archive, directory):
    if not archive:
        archive = directory / ARCHIVE
        urlretrieve(ARCHIVE_URL, archive)
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != ARCHIVE_SHA256:
        raise ValueError(f"L’empreinte de {archive} ne correspond pas à l’archive officielle.")
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


def invoke(executable, *args, cwd):
    try:
        completed = run(executable, *args, cwd=cwd)
    except subprocess.TimeoutExpired:
        return result("timeout", "The process exceeded 30 seconds.", detail_fr="Le processus a dépassé 30 secondes.")
    except OSError as exc:
        return result("blocked", str(exc))
    if completed.returncode:
        status = "crash" if completed.returncode < 0 else "blocked"
        detail = completed.stderr.strip() or completed.stdout.strip()
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


def comparisons(executables, cwd):
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
                     "titleFr": probe.title_fr,
                     "code": f"import {probe.module}\n\n{snippet}", "source": source_url(probe.upstream),
                     "sourceTest": probe.upstream, "outcomes": outcomes})
    return rows


def upstream_results(executables, tests, cwd):
    rows = []
    for module, methods in UPSTREAM.items():
        for method in methods:
            outcomes = {}
            for runtime in ("cpython", "pypy"):
                observation = invoke(executables[runtime], str(ROOT / "upstream.py"),
                                     str(tests.parent), method, cwd=cwd)
                try:
                    outcomes[runtime] = observation if isinstance(observation, dict) else json.loads(observation)
                except ValueError:
                    outcomes[runtime] = result("blocked", observation)
            if outcomes["cpython"]["status"] != "passed":
                observed = outcomes["pypy"]
                outcomes["pypy"] = result("unverified", f"Observed status: {observed['status']}\n{observed['detail']}",
                                          detail_fr=f"État observé : {observed['status']}\n{observed.get('detailFr', observed['detail'])}")
            rows.append({"id": method, "module": module, "title": method.split(".")[-1],
                         "source": source_url(method), "sourceTest": method, "outcomes": outcomes})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpython", default=sys.executable, help=f"Binaire de référence {CPYTHON_VERSION}")
    parser.add_argument("--pypy", default="pypy3.11", help=f"Binaire PyPy ciblant Python {CPYTHON_VERSION}")
    parser.add_argument("--graalpy", help="Binaire GraalPy autonome. Ajouté au corpus commun si fourni.")
    parser.add_argument("--rustpython", help="Binaire RustPython. Ajouté au corpus commun si fourni.")
    parser.add_argument("--applications", action="store_true", help="Mesurer Django, Bottle et NumPy dans un dossier temporaire")
    parser.add_argument("--source", type=Path, help=f"Archive officielle {ARCHIVE}, téléchargée si omise")
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="Dossier du site généré")
    args = parser.parse_args()

    try:
        executables = {}
        for runtime in RUNTIME_NAMES:
            command = getattr(args, runtime)
            if command:
                path = shutil.which(command)
                if not path:
                    raise ValueError(f"Binaire introuvable : {command}")
                executables[runtime] = os.path.abspath(path)

        with tempfile.TemporaryDirectory(prefix="python-conformity-") as temp:
            directory = Path(temp)
            runtimes = [identify(path, runtime, directory) for runtime, path in executables.items()]
            tests = extract_tests(args.source, directory)
            report = {
                "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "platform": f"{platform.system()} {platform.release()} · {platform.machine()}",
                "reference": CPYTHON_VERSION,
                "runtimes": runtimes,
                "common": comparisons(executables, directory),
                "upstream": upstream_results(executables, tests, directory),
                "applications": application_results(executables, directory, invoke) if args.applications else [],
            }
            generate(report, args.output)
    except (OSError, ValueError, subprocess.TimeoutExpired, tarfile.TarError) as exc:
        parser.exit(1, f"Mesure interrompue : {exc}\n")

    print(f"{len(report['common'])} cas communs · {len(report['upstream'])} tests amont · {args.output / 'index.html'}")
    for suite in ("common", "upstream", "applications"):
        for runtime in executables:
            outcomes = [row["outcomes"][runtime]["status"] for row in report[suite] if runtime in row["outcomes"]]
            if outcomes:
                print(f"{suite} / {runtime}: {outcomes.count('passed')}/{len(outcomes)} réussis")
    return int(any(row["outcomes"]["cpython"]["status"] != "passed"
                   for suite in ("common", "upstream") for row in report[suite]))


if __name__ == "__main__":
    sys.exit(main())
