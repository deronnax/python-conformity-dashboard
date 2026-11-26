"""The Python versions the dashboard measures, each against its own CPython reference.

Every interpreter in a measurement implements the same Python version as the
reference, so a difference is never a version difference. Each version has its
own package ranking, because a release is chosen for the Python version it
supports, and its own NumPy wheels.
"""

from dataclasses import dataclass, field
from pathlib import Path

from applications import PYPI, Wheel


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Reference:
    cpython: str
    archive_sha256: str
    # NumPy 2.4.4 wheels for the scenario, per interpreter. An interpreter without
    # an entry has no pinned wheel and reports "No wheel".
    numpy: dict = field(default_factory=dict)
    # Keys of notes the dashboard shows for this version, such as a beta interpreter.
    notes: tuple = ()

    @property
    def minor(self):
        return self.cpython.rpartition(".")[0]

    @property
    def archive(self):
        return f"Python-{self.cpython}.tar.xz"

    @property
    def archive_url(self):
        return f"https://www.python.org/ftp/python/{self.cpython}/{self.archive}"

    @property
    def ranking(self):
        return ROOT / f"pypi-packages-{self.minor}.json"

    @property
    def source_root(self):
        return f"https://github.com/python/cpython/blob/v{self.cpython}/Lib/"

    @property
    def docs_root(self):
        return f"https://docs.python.org/{self.minor}/library/"


# The free-threaded build implements Python 3.14 and is measured with the default version.
FREETHREADED_NUMPY = Wheel(
    PYPI + "5f/86/2acbda8cc2af5f3d7bfc791192863b9e3e19674da7b5e533fded124d1299/"
    "numpy-2.4.4-cp314-cp314t-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
    "b268594bccac7d7cf5844c7732e3f20c50921d94e36d7ec9b79e9857694b1b2f",
)

REFERENCES = {
    # PyPI has no NumPy 2.4.4 wheel for PyPy 3.12, and Oracle's GraalPy wheels for
    # this ABI stop at NumPy 2.2.4.
    "3.12": Reference("3.12.15", "c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a", {
        "cpython": Wheel(
            PYPI + "0a/0d/0e3ecece05b7a7e87ab9fb587855548da437a061326fff64a223b6dcb78a/"
            "numpy-2.4.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "81f4a14bee47aec54f883e0cad2d73986640c1590eb9bfaaba7ad17394481e6e",
        ),
        "freethreaded": FREETHREADED_NUMPY,
    }, notes=("pypyBeta",)),
    # The PyPy wheel is built for the PyPy 7.3 ABI, which PyPy 8 does not load: the
    # scenario reports it as another ABI. Oracle's GraalPy wheels for this ABI stop
    # at NumPy 1.26.4.
    "3.11": Reference("3.11.17", "bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599", {
        "cpython": Wheel(
            PYPI + "cf/c5/9fcb7e0e69cef59cf10c746b84f7d58b08bc66a6b7d459783c5a4f6101a6/"
            "numpy-2.4.4-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "df3775294accfdd75f32c74ae39fcba920c9a378a2fc18a12b6820aa8c1fb502",
        ),
        "pypy": Wheel(
            PYPI + "a2/c8/f0a45426d6d21e7ea3310a15cf90c43a14d9232c31a837702dba437f3373/"
            "numpy-2.4.4-pp311-pypy311_pp73-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "9b2aec6af35c113b05695ebb5749a787acd63cafc83086a05771d1e1cd1e555f",
        ),
        "freethreaded": FREETHREADED_NUMPY,
    }),
}
# PyPy for Python 3.12 is a beta, so the dashboard opens on Python 3.11.
DEFAULT = "3.11"
