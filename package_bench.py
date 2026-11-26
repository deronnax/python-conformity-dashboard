"""Install pinned packages and check imports in disposable wheel-only environments."""

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import BadZipFile

from applications import PYPI, Wheel, prepare
from smoke import SMOKE


ROOT = Path(__file__).resolve().parent
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
import traceback

directories, project, version, name, check = sys.argv[1:]
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
    outcome = {"status": "passed", "detail": "", "level": "functional" if check else "import"}
    if check:
        try:
            exec(compile(check, "<functional check>", "exec"), {"__name__": "__check__"})
        except Exception:
            lines = traceback.format_exc().strip().splitlines()
            outcome = {"status": "functionError", "detail": "\\n".join(lines[-6:]), "level": "functional"}
print(json.dumps(outcome))
"""

# Heavy scientific packages compile their bytecode on first import, and GraalPy
# starts a JVM, so a short limit reports slowness as a failure.
IMPORT_TIMEOUT = 60
MISSING_DISTRIBUTION = re.compile(r"No matching distribution found for ([A-Za-z0-9][A-Za-z0-9._-]*)(\S*)")
# pip explains a ResolutionImpossible with lines such as
# "    referencing 0.37.0 depends on rpds-py>=0.7.0".
CONFLICT = re.compile(r"^\s+(\S+) \S+ depends on ([^;]+?)\s*(?:;.*)?$", re.MULTILINE)
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

    A PyPy 3.12 wheel tagged pp312-pypy312_pp73 matches a PyPy 8 interpreter
    (pp312, pypy312_pp80) except for its ABI. A pp310 wheel targets another
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


def other_python_versions(filenames, tag):
    """Return the interpreter tags of wheels built for this implementation and platform,
    but for another Python version.

    cryptography 50.0.2 publishes pp311-pypy311_pp73 wheels for Linux and none for
    pp312: a PyPy 3.12 interpreter finds no wheel, although the project builds for PyPy.
    Version-independent wheels (abi3, none) do not count: when pip rejects them, the
    reason is not the Python version.
    """
    implementation = re.match(r"[a-z]+", tag["interpreter"])[0]
    system, machine = platform_family(tag["platform"])
    found = set()
    for filename in filenames:
        if not filename.endswith(".whl"):
            continue
        interpreters, abis, platforms = filename[:-4].split("-")[-3:]
        if all(abi in ("none", "abi3") for abi in abis.split(".")):
            continue
        if not any(
            platform_family(name)[0] == system and (platform_family(name)[1] in (machine, "universal2"))
            for name in platforms.split(".")
        ):
            continue
        found.update(name for name in interpreters.split(".")
                     if re.fullmatch(implementation + r"\d+", name) and name != tag["interpreter"])
    return sorted(found, key=lambda name: [int(part) for part in re.findall(r"\d+", name)])


@lru_cache(maxsize=None)
def project_releases(project):
    """Every release of a project on PyPI, as {version: [filenames]}."""
    url = f"https://pypi.org/pypi/{quote(project, safe='')}/json"
    with urlopen(url, timeout=20) as response:
        return {version: [item["filename"] for item in files if not item.get("yanked")]
                for version, files in json.load(response)["releases"].items()}


def newest_matching(project, specifier):
    """Newest stable release of project that satisfies specifier, or None.

    pip's vendored packaging is used, so the harness needs no dependency of its own."""
    try:
        from pip._vendor.packaging.specifiers import InvalidSpecifier, SpecifierSet
        from pip._vendor.packaging.version import InvalidVersion, Version
    except ImportError:
        return None
    try:
        allowed = SpecifierSet(specifier)
    except InvalidSpecifier:
        return None
    candidates = []
    for text, files in project_releases(project).items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if files and not version.is_prerelease and version in allowed:
            candidates.append((version, text))
    return max(candidates)[1] if candidates else None


def blocking_requirements(output, project):
    """Requirements of other projects that stopped pip, as (name, specifier) pairs."""
    found = {}
    for match in MISSING_DISTRIBUTION.finditer(output):
        if canonical(match[1]) != canonical(project):
            found.setdefault(canonical(match[1]), (match[1], match[2]))
    for match in CONFLICT.finditer(output):
        requirement = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(.*)", match[2].strip())
        if requirement and canonical(requirement[1]) != canonical(project):
            found.setdefault(canonical(requirement[1]), (requirement[1], requirement[2].replace(" ", "")))
    return list(found.values())


def describe_dependency(name, specifier, tag):
    """Why a dependency has no usable wheel: another ABI, another Python version, or none."""
    blocker = {"name": name, "requirement": name + specifier}
    try:
        version = newest_matching(name, specifier)
        files = project_releases(name).get(version, []) if version else []
    except (OSError, ValueError, KeyError):
        return blocker
    if version:
        blocker["version"] = version
    if tag and files:
        abis = foreign_abis(files, tag)
        versions = other_python_versions(files, tag)
        if abis:
            blocker.update(cause="otherAbi", published=abis)
        elif versions:
            blocker.update(cause="otherPython", published=versions)
        else:
            blocker["cause"] = "noWheel"
    return blocker


def blocked_by(package, output, tag, root):
    """Attribute a failed installation to the dependency that stopped it, when pip names one."""
    requirements = blocking_requirements(output, package["project"])
    if not requirements:
        return None
    blocker = describe_dependency(*requirements[0], tag)
    detail = output.strip().splitlines()
    detail = "\n".join(line for line in detail if line.startswith("ERROR:") or "depends on" in line)
    outcome = result("dependency", detail.replace(str(root), "<test directory>")[:1000])
    outcome["blocker"] = blocker
    if len(requirements) > 1:
        outcome["otherBlockers"] = [name for name, _ in requirements[1:]]
    return outcome


def release_files(project, version):
    url = f"https://pypi.org/pypi/{quote(project, safe='')}/{quote(version, safe='')}/json"
    with urlopen(url, timeout=20) as response:
        return [item["filename"] for item in json.load(response)["urls"]]


def missing_wheel(package, line, tag, root):
    """Separate a release published for another ABI or another Python version of this
    implementation from a missing wheel."""
    detail = line.replace(str(root), "<test directory>")
    match = MISSING_DISTRIBUTION.search(line)
    if tag and match and canonical(match[1]) == canonical(package["project"]):
        try:
            files = release_files(package["project"], package["version"])
        except (OSError, ValueError, KeyError):
            files = []
        abis = foreign_abis(files, tag)
        versions = other_python_versions(files, tag)
        if abis:
            published = ", ".join(abis)
            return result(
                "otherAbi",
                f"Wheels published for {published}. This interpreter requires {tag['abi']}.",
                detail_fr=f"Wheels publiés pour {published}. Cet interpréteur exige {tag['abi']}.",
            )
        if versions:
            published = ", ".join(versions)
            return result(
                "otherPython",
                f"Wheels published for {published} only. This interpreter is {tag['interpreter']}.",
                detail_fr=f"Wheels publiés pour {published} seulement. Cet interpréteur est {tag['interpreter']}.",
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
            output = installation.stderr + installation.stdout
            dependency = blocked_by(package, output, tag, root)
            if dependency:
                return dependency
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
                              version, package["module"], SMOKE.get(project, ""), timeout=IMPORT_TIMEOUT)
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


def pure_python(package):
    """True when the pinned release publishes a wheel that any interpreter can install."""
    try:
        files = release_files(package["project"], package["version"])
    except (OSError, ValueError, KeyError):
        return None
    return any(name.endswith("-none-any.whl") for name in files)


def native_only(package):
    if package["purePython"] is None:
        return result("blocked", "PyPI did not list the release files.",
                      detail_fr="PyPI n’a pas donné la liste des fichiers de la version.")
    return result("nativeOnly", "The release publishes no pure-Python wheel.",
                  detail_fr="La version ne publie aucun wheel purement Python.")


def package_results(executables, directory, ranking_path, pure_only=()):
    """Install and import each ranked package. Interpreters in pure_only, which cannot
    load extension modules, are tested only on releases with a pure-Python wheel."""
    ranking = json.loads(Path(ranking_path).read_text(encoding="utf-8"))
    root = directory / "package-bench"
    root.mkdir()
    try:
        pip = prepare((PIP,), root / "installer")
    except (OSError, ValueError, BadZipFile) as exc:
        print(f"Package installer provisioning: {exc}")
        for package in ranking["items"]:
            package["outcomes"] = {runtime: result("installerUnavailable") for runtime in executables}
        return ranking
    # The harness reads requirements with pip's vendored packaging.
    import sys
    if str(pip) not in sys.path:
        sys.path.append(str(pip))
    for package in ranking["items"]:
        package["purePython"] = pure_python(package)
        if package["project"] in SMOKE:
            package["check"] = SMOKE[package["project"]].strip()
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
                if runtime not in pure_only or package["purePython"]
            }
            for package in ranking["items"]
        ]
        for package, checks in zip(ranking["items"], tasks):
            package["outcomes"] = {
                runtime: checks[runtime].result() if runtime in checks
                else unavailable.get(runtime) or native_only(package)
                for runtime in executables
            }
    return ranking
