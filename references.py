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
class Archive:
    url: str
    sha256: str


STANDALONE = "https://github.com/astral-sh/python-build-standalone/releases/download/20261021/"
FREETHREADED = Archive(STANDALONE + "cpython-3.14.9%2B20261021-x86_64-unknown-linux-gnu-freethreaded-install_only.tar.gz",
                       "298aff66cb6e46777dae42441e3bf559c708fbf5e001afc4d3e93b0d245c021d")
# RustPython is built from source, once per measurement, with the bundled standard library.
RUSTPYTHON_SOURCE = Archive("https://github.com/RustPython/RustPython/archive/refs/tags/0.6.0.tar.gz",
                            "bf290cf7a70f813758819d895868b2b49b9edea1f10de3524df2cae1f2d58a4d")


def cpython_build(release, sha256):
    return Archive(STANDALONE + f"cpython-{release}%2B20261021-x86_64-unknown-linux-gnu-install_only.tar.gz", sha256)


@dataclass(frozen=True)
class Reference:
    cpython: str
    archive_sha256: str
    # Linux x86-64 archives of the interpreters measured with this version, by id.
    # RustPython is measured with every version and built from RUSTPYTHON_SOURCE.
    interpreters: dict
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
    # Listed from the oldest version, which the version switch shows first.
    # The PyPy wheel is built for the PyPy 7.3 ABI, which PyPy 8 does not load: the
    # scenario reports it as another ABI. Oracle's GraalPy wheels for this ABI stop
    # at NumPy 1.26.4.
    "3.11": Reference("3.11.17", "bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599", {
        "cpython": cpython_build("3.11.17", "7cc8d9dce9ea23c31267e7f244005c8979da04794b7737a3a30e62b03abeb120"),
        "pypy": Archive("https://downloads.python.org/pypy/pypy3.11-v8.0.1-linux64.tar.gz",
                        "706965bcf372752ba69dafd59d860e51bc2fadbb0f8a47cec3426125d7058ceb"),
        # GraalPy 24.2 is the last release that implements Python 3.11.
        "graalpy": Archive("https://github.com/oracle/graalpython/releases/download/graal-24.2.2/"
                           "graalpy-community-24.2.2-linux-amd64.tar.gz",
                           "384642677b76c26d6be1cf6bce2bc94d49df53845dd506414d95e2322bc9ac5d"),
        # The free-threaded build implements Python 3.14: it is measured once.
        "freethreaded": FREETHREADED,
    }, {
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
    # PyPI has no NumPy 2.4.4 wheel for PyPy 3.12, and Oracle's GraalPy wheels for
    # this ABI stop at NumPy 2.2.4.
    "3.12": Reference("3.12.15", "c2c4321961fab0fb999d66e0cecf521c2ab3994c7992873ea99e306c1094fd5a", {
        "cpython": cpython_build("3.12.15", "5ff9f0602ce964a529ed1e8555d3abab6341926d724402ba9a15e9e877191124"),
        "pypy": Archive("https://downloads.python.org/pypy/pypy3.12-v8.0.1-linux64.tar.gz",
                        "aeed27797777296d9c94e53bdfa608804696dbd4ff9f2213003cce064ee46ef8"),
        "graalpy": Archive("https://github.com/oracle/graalpython/releases/download/graal-25.2.4/"
                           "graalpy3.12-community-25.2.4-linux-amd64.tar.gz",
                           "98af303a6b714bde39077354733254f78023ddef06d61e14cb66a3a01f10ae82"),
    }, {
        "cpython": Wheel(
            PYPI + "0a/0d/0e3ecece05b7a7e87ab9fb587855548da437a061326fff64a223b6dcb78a/"
            "numpy-2.4.4-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "81f4a14bee47aec54f883e0cad2d73986640c1590eb9bfaaba7ad17394481e6e",
        ),
        "freethreaded": FREETHREADED_NUMPY,
    }, notes=("pypyBeta",)),
    # PyPy has no release for Python 3.13. Oracle's GraalPy wheels of NumPy 2.4.4 are
    # built for GraalPy 25.3, not for GraalPy 25.6.
    "3.13": Reference("3.13.17", "6020bd10aff3bf4821be16f088ebb1591beb7b811dcd8fab1da8f7c22a7b27e7", {
        "cpython": cpython_build("3.13.17", "cbda6f7767884fc456860b11fd184391a9320cae00a86c0f49a1c7ac6e236f7a"),
        "graalpy": Archive("https://github.com/oracle/graalpython/releases/download/graal-25.6.5/"
                           "graalpy3.13-community-25.6.5-linux-amd64.tar.gz",
                           "9c9d68730d4e6de5f5e96acddab6f0625b6534026a128ee72a1d5cfe59621520"),
    }, {
        "cpython": Wheel(
            PYPI + "d1/73/a9d864e42a01896bb5974475438f16086be9ba1f0d19d0bb7a07427c4a8b/"
            "numpy-2.4.4-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "c901b15172510173f5cb310eae652908340f8dede90fff9e3bf6c0d8dfd92f83",
        ),
        "freethreaded": FREETHREADED_NUMPY,
    }, notes=("noPypy313",)),
    # Neither PyPy nor GraalPy has a release for Python 3.14.
    "3.14": Reference("3.14.9", "e02d9ac21cebda6e46435369744a92c65cc7cd8669697694122cf97ffacd1e53", {
        "cpython": cpython_build("3.14.9", "dfa4c5a40c47f338f41658017be550c72247c391e6bfb1fa4da03ebc8451abdf"),
    }, {
        "cpython": Wheel(
            PYPI + "98/7c/21252050676612625449b4807d6b695b9ce8a7c9e1c197ee6216c8a65c7c/"
            "numpy-2.4.4-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
            "27a8d92cd10f1382a67d7cf4db7ce18341b66438bdd9f691d7b0e48d104c2a9d",
        ),
        "freethreaded": FREETHREADED_NUMPY,
    }, notes=("noPypy314",)),
}
# PyPy for Python 3.12 is a beta, so the dashboard opens on Python 3.11.
DEFAULT = "3.11"


def site_layout(reference):
    """Where each version's dashboard lives: the default version at the root, the others in a folder."""
    return {"current": reference.minor,
            "versions": [(minor, "" if minor == DEFAULT else f"{minor}/") for minor in REFERENCES]}
