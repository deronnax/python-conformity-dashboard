"""Provision pinned third-party wheels and collect application results."""

import hashlib
import json
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class Wheel:
    url: str
    sha256: str

    @property
    def filename(self):
        return self.url.rsplit("/", 1)[1]


PYPI = "https://files.pythonhosted.org/packages/"
DJANGO = (
    Wheel(PYPI + "3c/fb/65b4e897d1268288a46457493d9aec6541be8be08e0093a93cc101c03ab2/django-5.2.19-py3-none-any.whl",
          "5965d974a5218a2b68a11dd1276434707f23886525c23f0598eccedaf4f4ca00"),
    Wheel(PYPI + "91/be/317c2c55b8bbec407257d45f5c8d1b6867abc76d12043f2d3d58c538a4ea/asgiref-3.11.0-py3-none-any.whl",
          "1db9021efadb0d9512ce8ffaf72fcef601c7b73a8807a1bb2ef143dc6b14846d"),
    Wheel(PYPI + "a9/5c/bfd6bd0bf979426d405cc6e71eceb8701b148b16c21d2dc3c261efc61c7b/sqlparse-0.5.3-py3-none-any.whl",
          "cf2196ed3418f3ba5de6af7e82c694a9fbdbfecccdfc72e281548517081f16ca"),
)
BOTTLE = (
    Wheel(PYPI + "83/f6/b55ec74cfe68c6584163faa311503c20b0da4c09883a41e8e00d6726c954/bottle-0.13.4-py2.py3-none-any.whl",
          "045684fbd2764eac9cdeb824861d1551d113e8b683d8d26e296898d3dd99a12e"),
)
# PyPI publishes NumPy 2.4.4 for PyPy 3.11 only, and Oracle publishes GraalPy wheels
# for the 25.0 ABI on Python 3.12, not for the 25.2 release tested here. An
# interpreter without an entry has no pinned wheel and reports "No wheel".
NUMPY = {
    "cpython": Wheel(
        PYPI + "0a/0d/0e3ecece05b7a7e87ab9fb587855548da437a061326fff64a223b6dcb78a/"
        "numpy-2.4.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        "81f4a14bee47aec54f883e0cad2d73986640c1590eb9bfaaba7ad17394481e6e",
    ),
    "freethreaded": Wheel(
        PYPI + "5f/86/2acbda8cc2af5f3d7bfc791192863b9e3e19674da7b5e533fded124d1299/"
        "numpy-2.4.4-cp314-cp314t-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        "b268594bccac7d7cf5844c7732e3f20c50921d94e36d7ec9b79e9857694b1b2f",
    ),
}

CHECKS = (
    ("django-template", "Django", "5.2.19", DJANGO),
    ("django-sqlite", "Django", "5.2.19", DJANGO),
    ("bottle-route", "Bottle", "0.13.4", BOTTLE),
    ("numpy-array", "NumPy", "2.4.4", None),
)
WORKER = Path(__file__).with_name("application_checks.py")


def prepare(wheels, directory):
    directory.mkdir()
    for wheel in wheels:
        archive = directory / wheel.filename
        with urlopen(wheel.url, timeout=30) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target)
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != wheel.sha256:
                raise ValueError(f"Wheel digest mismatch: {wheel.filename}")
        # These pinned wheels can be imported in place after ZIP extraction.
        with ZipFile(archive) as package:
            package.extractall(directory)
        archive.unlink()
    return directory


def numpy_outcome(executable, site, wheel, invoke, directory):
    suffix = invoke(executable, "-c", "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))", cwd=directory)
    if isinstance(suffix, dict):
        return suffix
    extension = site / "numpy" / "_core" / f"_multiarray_umath{suffix}"
    if not extension.is_file():
        return {
            "status": "otherAbi",
            "detail": f"This interpreter loads *{suffix} extensions. The pinned wheel is {wheel.filename}.",
            "detailFr": f"Cet interpréteur charge les extensions *{suffix}. Le wheel épinglé est {wheel.filename}.",
        }
    return None


def application_results(executables, directory, invoke):
    prepared = {}
    results = []
    for name, package, version, wheels in CHECKS:
        outcomes = {}
        for runtime, executable in executables.items():
            native = wheels is None
            if native and (platform.system(), platform.machine()) != ("Linux", "x86_64"):
                outcomes[runtime] = {"status": "skipped", "detail": "Linux x86-64"}
                continue
            if native and runtime not in NUMPY:
                outcomes[runtime] = {"status": "noWheel", "detail": ""}
                continue
            dependencies = (NUMPY[runtime],) if native else wheels
            if dependencies not in prepared:
                target = directory / f"application-wheels-{len(prepared)}"
                try:
                    prepared[dependencies] = prepare(dependencies, target)
                except (OSError, ValueError, BadZipFile) as exc:
                    print(f"{package} provisioning: {exc}")
                    prepared[dependencies] = {"status": "blocked", "detail": ""}
            site = prepared[dependencies]
            if isinstance(site, dict):
                outcomes[runtime] = site
                continue
            if native:
                unavailable = numpy_outcome(executable, site, dependencies[0], invoke, directory)
                if unavailable is not None:
                    outcomes[runtime] = unavailable
                    continue
            observed = invoke(executable, str(WORKER), name, str(site), cwd=directory)
            try:
                outcomes[runtime] = observed if isinstance(observed, dict) else json.loads(observed)
            except ValueError:
                print(f"{runtime} returned unreadable output for {name}")
                outcomes[runtime] = {"status": "blocked", "detail": ""}
        results.append({"id": name, "package": package, "version": version, "outcomes": outcomes})
    return results
