"""Install pinned packages and check imports in disposable wheel-only environments."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from applications import PYPI, Wheel, prepare


ROOT = Path(__file__).resolve().parent
RANKING = ROOT / "pypy-packages.json"
PIP = Wheel(
    PYPI + "5d/95/6b5cb3461ea5673ba0995989746db58eb18b91b54dbf331e72f569540946/pip-26.1.2-py3-none-any.whl",
    "382ff9f685ee3bc25864f820aa50505825f10f5458ffff07e30a6d96e5715cab",
)

START_PIP = """
import runpy
import sys

sys.path.insert(0, sys.argv.pop(1))
runpy.run_module("pip", run_name="__main__")
"""

IMPORT_PACKAGE = """
from importlib import import_module, metadata
from pathlib import Path
import json
import site
import sys

directory, project, version, name = sys.argv[1:]
sys.path.insert(0, directory)
site.addsitedir(directory)
installed_directory = Path(directory).resolve()
try:
    installed = metadata.version(project)
    if installed != version:
        raise RuntimeError(f"Expected {version}, found {installed}")
    module = import_module(name)
    filename = getattr(module, "__file__", None)
    paths = [filename] if filename else getattr(module, "__path__", ())
    if not any(Path(path).resolve().is_relative_to(installed_directory) for path in paths):
        raise ImportError(f"{name} resolved outside the package directory")
except Exception as exc:
    outcome = {"status": "importError", "detail": f"{type(exc).__name__}: {exc}"}
else:
    outcome = {"status": "passed", "detail": ""}
print(json.dumps(outcome))
"""


def launch(executable, cwd, *arguments, timeout):
    inherited = ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")
    environment = {key: os.environ[key] for key in inherited if key in os.environ}
    environment.update({
        "PIP_CONFIG_FILE": os.devnull,
        "XDG_CACHE_HOME": str(cwd / "cache"),
        "MPLCONFIGDIR": str(cwd / "matplotlib"),
        "OPENBLAS_NUM_THREADS": "1",
    })
    return subprocess.run(
        [executable, "-I", "-S", "-B", *arguments],
        cwd=cwd,
        env=environment,
        timeout=timeout,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def result(status, detail=""):
    return {"status": status, "detail": detail}


def diagnostic(completed, directory):
    lines = (completed.stderr.strip() or completed.stdout.strip()).splitlines()
    selected = [line for line in lines if line.startswith("ERROR:")]
    return "\n".join((selected or lines)[-3:]).replace(str(directory), "<test directory>")[:1000]


def install_and_import(package, runtime, executable, root, pip):
    project, version = package["project"], package["version"]
    with TemporaryDirectory(prefix=f"{runtime}-{project}-", dir=root) as temporary:
        working = Path(temporary)
        site = working / "packages"
        arguments = [
            "--isolated", "--disable-pip-version-check", "--no-input", "--no-cache-dir",
            "install", "--only-binary=:all:", "--index-url", "https://pypi.org/simple/",
            "--timeout", "10", "--retries", "1", "--target", str(site),
        ]
        if runtime == "graalpy":
            arguments.extend(("--extra-index-url", "https://gds.oracle.com/repositories/pypi/public-release/"))
        try:
            installation = launch(executable, working, "-c", START_PIP, str(pip),
                                  *arguments, f"{project}=={version}", timeout=65)
        except subprocess.TimeoutExpired:
            return result("installTimeout")
        except OSError:
            return result("blocked")
        if installation.returncode:
            for line in reversed(installation.stderr.splitlines()):
                if "No matching distribution found" in line:
                    return result("noWheel", line.replace(str(root), "<test directory>"))
            return result("installError", diagnostic(installation, root))

        try:
            imported = launch(executable, working, "-c", IMPORT_PACKAGE, str(site), project, version,
                              package["module"], timeout=20)
        except subprocess.TimeoutExpired:
            return result("timeout")
        except OSError:
            return result("blocked")
        if imported.returncode:
            return result("crash" if imported.returncode < 0 else "importError", diagnostic(imported, root))
        try:
            outcome = json.loads(imported.stdout.splitlines()[-1])
        except (IndexError, ValueError):
            return result("blocked", diagnostic(imported, root))
        outcome["detail"] = outcome["detail"].replace(str(root), "<test directory>")[:1000]
        return outcome


def package_results(executables, directory):
    ranking = json.loads(RANKING.read_text(encoding="utf-8"))
    root = directory / "package-bench"
    root.mkdir()
    try:
        pip = prepare((PIP,), root / "installer")
    except (OSError, ValueError, BadZipFile) as exc:
        print(f"Package installer provisioning: {exc}")
        for package in ranking["items"]:
            package["outcomes"] = {runtime: result("installerUnavailable") for runtime in executables}
        return ranking
    active = {}
    unavailable = {}
    for runtime, executable in executables.items():
        try:
            check = launch(executable, root, "-c", START_PIP, str(pip), "--version", timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            unavailable[runtime] = result("installerUnavailable")
        else:
            if check.returncode:
                unavailable[runtime] = result("installerUnavailable", diagnostic(check, root))
            else:
                active[runtime] = executable

    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            {
                runtime: executor.submit(install_and_import, package, runtime, executable, root, pip)
                for runtime, executable in active.items()
            }
            for package in ranking["items"]
        ]
        for package, checks in zip(ranking["items"], tasks):
            package["outcomes"] = {
                runtime: checks[runtime].result() if runtime in checks else unavailable[runtime]
                for runtime in executables
            }
    return ranking
