"""Install pinned packages and check imports in disposable wheel-only environments."""

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import BadZipFile

from applications import PYPI, Wheel, prepare


ROOT = Path(__file__).resolve().parent
RANKING = ROOT / "pypi-packages.json"
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

# pip selects wheels with the first tag of this list, so it names the ABI the
# interpreter actually requires.
WHEEL_TAG = """
import json
import sys

sys.path.insert(0, sys.argv[1])
from pip._vendor.packaging.tags import sys_tags

tag = next(iter(sys_tags()))
print(json.dumps({"interpreter": tag.interpreter, "abi": tag.abi, "platform": tag.platform}))
"""

IMPORT_PACKAGE = """
from importlib import import_module, metadata
from pathlib import Path
import json
import os
import site
import sys

directories, project, version, name = sys.argv[1:]
installed_directories = []
for directory in reversed(directories.split(os.pathsep)):
    sys.path.insert(0, directory)
    site.addsitedir(directory)
    installed_directories.append(Path(directory).resolve())
try:
    installed = metadata.version(project)
    if installed != version:
        raise RuntimeError(f"Expected {version}, found {installed}")
    module = import_module(name)
    filename = getattr(module, "__file__", None)
    paths = [filename] if filename else getattr(module, "__path__", ())
    if not any(Path(path).resolve().is_relative_to(installed) for path in paths for installed in installed_directories):
        raise ImportError(f"{name} resolved outside the package directory")
except Exception as exc:
    outcome = {"status": "importError", "detail": f"{type(exc).__name__}: {exc}"}
else:
    outcome = {"status": "passed", "detail": ""}
print(json.dumps(outcome))
"""

# Heavy scientific packages compile their bytecode on first import, and GraalPy
# starts a JVM, so a short limit reports slowness as a failure.
IMPORT_TIMEOUT = 60
MISSING_DISTRIBUTION = re.compile(r"No matching distribution found for ([A-Za-z0-9][A-Za-z0-9._-]*)")
PLATFORM = re.compile(r"^(manylinux|musllinux|macosx|linux|win)(?:\d+|_\d+_\d+)?_(.+)$")


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


def result(status, detail="", *, detail_fr=None):
    outcome = {"status": status, "detail": detail}
    if detail_fr is not None:
        outcome["detailFr"] = detail_fr
    return outcome


def diagnostic(completed, directory):
    lines = (completed.stderr.strip() or completed.stdout.strip()).splitlines()
    selected = [line for line in lines if line.startswith("ERROR:")]
    return "\n".join((selected or lines)[-3:]).replace(str(directory), "<test directory>")[:1000]


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def platform_family(platform):
    match = PLATFORM.match(platform)
    if not match:
        return platform, ""
    system = "linux" if match[1] in ("manylinux", "musllinux", "linux") else match[1]
    return system, match[2]


def foreign_abis(filenames, tag):
    """Return the ABIs of wheels built for this interpreter tag and platform but another ABI.

    A PyPy 3.11 wheel tagged pp311-pypy311_pp73 matches a PyPy 8 interpreter
    (pp311, pypy311_pp80) except for its ABI. A pp310 wheel targets another
    Python version and does not count.
    """
    system, machine = platform_family(tag["platform"])
    found = set()
    for filename in filenames:
        if not filename.endswith(".whl"):
            continue
        interpreters, abis, platforms = filename[:-4].split("-")[-3:]
        if tag["interpreter"] not in interpreters.split("."):
            continue
        if not any(
            platform_family(name)[0] == system and (platform_family(name)[1] in (machine, "universal2"))
            for name in platforms.split(".")
        ):
            continue
        found.update(abi for abi in abis.split(".") if abi not in ("none", "abi3", tag["abi"]))
    return sorted(found)


def release_files(project, version):
    url = f"https://pypi.org/pypi/{quote(project, safe='')}/{quote(version, safe='')}/json"
    with urlopen(url, timeout=20) as response:
        return [item["filename"] for item in json.load(response)["urls"]]


def missing_wheel(package, line, tag, root):
    """Separate a release published for another ABI of this implementation from a missing wheel."""
    detail = line.replace(str(root), "<test directory>")
    match = MISSING_DISTRIBUTION.search(line)
    if tag and match and canonical(match[1]) == canonical(package["project"]):
        try:
            abis = foreign_abis(release_files(package["project"], package["version"]), tag)
        except (OSError, ValueError, KeyError):
            abis = []
        if abis:
            published = ", ".join(abis)
            return result(
                "otherAbi",
                f"Wheels published for {published}. This interpreter requires {tag['abi']}.",
                detail_fr=f"Wheels publiés pour {published}. Cet interpréteur exige {tag['abi']}.",
            )
    return result("noWheel", detail)


def site_directories(prefix):
    return [str(path) for path in sorted(prefix.glob("**/site-packages")) if path.is_dir()]


def install_arguments(prefix, runtime):
    # --prefix keeps the interpreter's bundled distributions visible to pip,
    # such as cffi on PyPy. --target would reinstall them from PyPI.
    arguments = [
        "--isolated", "--disable-pip-version-check", "--no-input", "--no-cache-dir",
        "install", "--only-binary=:all:", "--index-url", "https://pypi.org/simple/",
        "--timeout", "10", "--retries", "1", "--no-warn-script-location", "--prefix", str(prefix),
    ]
    if runtime == "graalpy":
        arguments.extend(("--extra-index-url", "https://gds.oracle.com/repositories/pypi/public-release/"))
    return arguments


def install_and_import(package, runtime, executable, root, pip, tag):
    project, version = package["project"], package["version"]
    with TemporaryDirectory(prefix=f"{runtime}-{project}-", dir=root) as temporary:
        working = Path(temporary)
        prefix = working / "prefix"
        arguments = install_arguments(prefix, runtime)
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
                    return missing_wheel(package, line, tag, root)
            return result("installError", diagnostic(installation, root))

        directories = site_directories(prefix)
        if not directories:
            return result("installError", "pip did not create a site-packages directory.",
                          detail_fr="pip n’a pas créé de dossier site-packages.")
        try:
            imported = launch(executable, working, "-c", IMPORT_PACKAGE, os.pathsep.join(directories), project,
                              version, package["module"], timeout=IMPORT_TIMEOUT)
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


def wheel_tag(executable, root, pip):
    try:
        completed = launch(executable, root, "-c", WHEEL_TAG, str(pip), timeout=20)
        return json.loads(completed.stdout.splitlines()[-1]) if completed.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError, ValueError):
        return None


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
    tags = {}
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
                tag = wheel_tag(executable, root, pip)
                if tag:
                    tags[runtime] = tag
    ranking["tags"] = tags

    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            {
                runtime: executor.submit(install_and_import, package, runtime, executable, root, pip, tags.get(runtime))
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
