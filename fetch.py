"""Download the interpreters of a measured Python version into runtimes/.

    python3 fetch.py 3.11                    # every interpreter of Python 3.11
    python3 fetch.py 3.11 cpython pypy       # some of them
    python3 fetch.py 3.11 rustpython-source  # the RustPython sources, to build it

Each archive is checked against its SHA-256 before it is extracted.
"""

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

from references import REFERENCES, RUSTPYTHON_SOURCE

RUNTIMES = Path(__file__).resolve().parent / "runtimes"
EXECUTABLES = {
    "cpython": "cpython/bin/python{minor}",
    "pypy": "pypy/bin/pypy{minor}",
    "graalpy": "graalpy/bin/graalpy",
    "freethreaded": "freethreaded/bin/python3.14t",
    # The binary built from RUSTPYTHON_SOURCE.
    "rustpython": "rustpython/rustpython",
}


def executable(runtime, minor, root=RUNTIMES):
    return Path(root) / EXECUTABLES[runtime].format(minor=minor)


def fetch(archive, target):
    with tempfile.TemporaryDirectory() as temporary:
        download = Path(temporary) / "archive.tar.gz"
        with urlopen(archive.url, timeout=120) as response, download.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        with download.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != archive.sha256:
                raise SystemExit(f"Digest mismatch: {archive.url}")
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(["tar", "-xzf", download, "--strip-components=1", "-C", target], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", choices=REFERENCES)
    parser.add_argument("names", nargs="*", help="Interpreters to download, or rustpython-source")
    arguments = parser.parse_args()
    archives = {**REFERENCES[arguments.version].interpreters, "rustpython-source": RUSTPYTHON_SOURCE}
    for name in arguments.names or REFERENCES[arguments.version].interpreters:
        if name not in archives:
            parser.error(f"Python {arguments.version} has no {name}. Choose among {', '.join(archives)}.")
        fetch(archives[name], RUNTIMES / name)
        print(f"{name}: {RUNTIMES / name}")


if __name__ == "__main__":
    main()
