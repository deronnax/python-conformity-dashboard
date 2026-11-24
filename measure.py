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
from urllib.request import urlretrieve

from corpus import CPYTHON_VERSION, PROBES, UPSTREAM, source_url


ROOT = Path(__file__).resolve().parent
ARCHIVE = f"Python-{CPYTHON_VERSION}.tar.xz"
ARCHIVE_URL = f"https://www.python.org/ftp/python/{CPYTHON_VERSION}/{ARCHIVE}"
ARCHIVE_SHA256 = "bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599"
RUNTIME_NAMES = {"cpython": "CPython", "pypy": "PyPy", "micropython": "MicroPython Unix", "graalpy": "GraalPy"}


def run(executable, runtime, *args, cwd):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("PYTHON") and key != "MICROPYPATH"}
    if runtime == "micropython":
        flags = []
        env["MICROPYPATH"] = ".frozen"
    else:
        flags = ["-I", "-S", "-B"]
    return subprocess.run([executable, *flags, *args], cwd=cwd, env=env, timeout=30,
                          capture_output=True, encoding="utf-8", errors="replace")


def identify(executable, runtime, cwd):
    info = run(executable, runtime, "-c", "import sys; print(sys.implementation.name); print(sys.version)", cwd=cwd)
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


def result(status, detail=""):
    return {"status": status, "detail": detail}


def invoke(executable, runtime, *args, cwd):
    try:
        completed = run(executable, runtime, *args, cwd=cwd)
    except subprocess.TimeoutExpired:
        return result("timeout", "Le processus a dépassé 30 secondes.")
    except OSError as exc:
        return result("blocked", str(exc))
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"Code {completed.returncode}"
        return result("crash" if completed.returncode < 0 else "blocked", detail)
    return completed.stdout.strip()


def observe(executable, runtime, probe, cwd):
    module, attribute = probe.api.split(".")
    code = f"""
try:
    module = __import__({module!r})
except ImportError as exc:
    if getattr(exc, 'name', None) == {module!r} or str(exc) == "no module named '{module}'":
        print('missing', {module!r})
    else:
        print('blocked', str(exc))
else:
    try:
        api = getattr(module, {attribute!r})
    except AttributeError:
        print('missing', {probe.api!r})
    else:
        try:
            value = {probe.expression}
        except Exception as exc:
            print('exception', type(exc).__name__)
        else:
            print('value', type(value).__name__, repr(value))
"""
    output = invoke(executable, runtime, "-c", code, cwd=cwd)
    if isinstance(output, dict):
        return output
    kind, _, payload = output.partition(" ")
    if kind in ("missing", "blocked"):
        return result(kind, payload)
    if kind == "exception":
        return f"exception: {payload}"
    if kind == "value":
        value_type, _, value = payload.partition(" ")
        try:
            return f"{value_type}: {ast.literal_eval(value)!r}"
        except (ValueError, SyntaxError):
            pass
    return result("blocked", f"Sortie illisible du processus : {output}")


def comparisons(executables, cwd):
    rows = []
    for probe in PROBES:
        baseline = observe(executables["cpython"], "cpython", probe, cwd)
        outcomes = {}
        for runtime, executable in executables.items():
            observation = baseline if runtime == "cpython" else observe(executable, runtime, probe, cwd)
            if isinstance(observation, dict):
                outcome = observation
            elif baseline != probe.expected:
                status = "blocked" if runtime == "cpython" else "unverified"
                outcome = result(status, f"Attendu dans le corpus : {probe.expected}\nObservé : {observation}")
            else:
                outcome = result("passed" if observation == baseline else "different", observation)
            outcomes[runtime] = outcome
        rows.append({"id": probe.id, "module": probe.module, "api": probe.api, "title": probe.title,
                     "code": probe.expression.replace("api(", probe.api + "("), "source": source_url(probe.upstream),
                     "sourceTest": probe.upstream, "outcomes": outcomes})
    return rows


def upstream_results(executables, tests, cwd):
    rows = []
    for module, methods in UPSTREAM.items():
        for method in methods:
            outcomes = {}
            for runtime in ("cpython", "pypy"):
                observation = invoke(executables[runtime], runtime, str(ROOT / "upstream.py"),
                                     str(tests.parent), method, cwd=cwd)
                try:
                    outcomes[runtime] = observation if isinstance(observation, dict) else json.loads(observation)
                except ValueError:
                    outcomes[runtime] = result("blocked", observation)
            if outcomes["cpython"]["status"] != "passed":
                observed = outcomes["pypy"]
                outcomes["pypy"] = result("unverified", f"État observé : {observed['status']}\n{observed['detail']}")
            rows.append({"id": method, "module": module, "title": method.split(".")[-1],
                         "source": source_url(method), "sourceTest": method, "outcomes": outcomes})
    return rows


def generate(report, output):
    output.mkdir(parents=True, exist_ok=True)
    data = json.dumps(report, indent=2, ensure_ascii=False)
    (output / "results.json").write_text(data + "\n", encoding="utf-8")
    for asset in ("dashboard.js", "styles.css"):
        shutil.copyfile(ROOT / "site" / asset, output / asset)
    template = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(template.replace("<!-- RESULTS -->", data.replace("<", r"\u003c")),
                                       encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpython", default=sys.executable, help=f"Binaire de référence {CPYTHON_VERSION}")
    parser.add_argument("--pypy", default="pypy3.11", help=f"Binaire PyPy ciblant Python {CPYTHON_VERSION}")
    parser.add_argument("--micropython", help="Binaire du port Unix. Ajouté au corpus commun si fourni.")
    parser.add_argument("--graalpy", help="Binaire GraalPy autonome. Ajouté au corpus commun si fourni.")
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
            }
            generate(report, args.output)
    except (OSError, ValueError, subprocess.TimeoutExpired, tarfile.TarError) as exc:
        parser.exit(1, f"Mesure interrompue : {exc}\n")

    print(f"{len(report['common'])} cas communs · {len(report['upstream'])} tests amont · {args.output / 'index.html'}")
    for suite in ("common", "upstream"):
        for runtime in executables:
            outcomes = [row["outcomes"][runtime]["status"] for row in report[suite] if runtime in row["outcomes"]]
            if outcomes:
                print(f"{suite} / {runtime}: {outcomes.count('passed')}/{len(outcomes)} réussis")
    return int(any(row["outcomes"]["cpython"]["status"] != "passed"
                   for suite in ("common", "upstream") for row in report[suite]))


if __name__ == "__main__":
    sys.exit(main())
