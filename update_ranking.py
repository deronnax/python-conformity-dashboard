"""Rebuild pypi-packages.json: the most downloaded PyPI projects and the release to test.

Run it with the reference CPython. The output is committed, so a dashboard
run always measures the same projects and releases until the ranking is
refreshed on purpose.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import package_bench
from references import REFERENCES
from applications import prepare


CLICKPY = "https://sql-clickhouse.clickhouse.com/"
SIMPLE = "https://pypi.org/simple/{project}/"
# The public ClickHouse server silently drops groups once an aggregation grows
# past a limit, which undercounts and omits projects. Restricting the groups to
# the 5,000 most downloaded projects keeps the aggregation exact.
QUERY = """SELECT project, sum(count) AS downloads
FROM pypi.pypi_downloads_per_day
PREWHERE project IN (SELECT project FROM pypi.pypi_downloads ORDER BY count DESC LIMIT 5000)
WHERE date >= '{start}' AND date < '{end}'
GROUP BY project
ORDER BY downloads DESC, project
LIMIT {limit} FORMAT JSONEachRow"""
# Import names that cannot be derived from the distribution's file list. They
# either live in a namespace package or leave the compiled code unloaded.
MODULES = {
    "cryptography": "cryptography.hazmat.bindings._rust",
    "opentelemetry-api": "opentelemetry.trace",
    "pillow": "PIL.Image",
    "protobuf": "google.protobuf",
}
FIND_MODULES = """
import json
import os
import sys
from importlib import metadata

directories, project = sys.argv[1:]
names = set()
for dist in metadata.distributions(name=project, path=directories.split(os.pathsep)):
    listed = (dist.read_text("top_level.txt") or "").split()
    for path in map(str, dist.files or ()):
        head, _, rest = path.partition("/")
        if head.endswith((".dist-info", ".data")) or head in ("..", "__pycache__", "bin"):
            continue
        listed.append(head if rest else head.partition(".")[0])
    names.update(listed)
print(json.dumps(sorted(names)))
"""


def packaging_modules():
    """Return pip's vendored Version and SpecifierSet, provisioning pip when it is absent."""
    try:
        from pip._vendor.packaging.specifiers import SpecifierSet
        from pip._vendor.packaging.version import Version
    except ImportError:
        site = prepare((package_bench.PIP,), Path(tempfile.mkdtemp(prefix="ranking-pip-")))
        sys.path.insert(0, str(site))
        from pip._vendor.packaging.specifiers import SpecifierSet
        from pip._vendor.packaging.version import Version
    return Version, SpecifierSet


def ranking(start, end, limit):
    query = QUERY.format(start=start, end=end, limit=limit)
    with urlopen(f"{CLICKPY}?{urlencode({'user': 'demo', 'query': query})}", timeout=120) as response:
        rows = [json.loads(line) for line in response.read().decode("utf-8").splitlines()]
    return query, [{"project": row["project"], "downloads": int(row["downloads"])} for row in rows]


def release_files(project):
    request = Request(SIMPLE.format(project=project), headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)["files"]


def choose_version(files, cutoff, python="3.12"):
    """Return the newest stable release with a wheel for this Python, uploaded before the cutoff date."""
    Version, SpecifierSet = packaging_modules()
    best = None
    for item in files:
        name = item["filename"]
        if not name.endswith(".whl") or item.get("yanked") or item.get("upload-time", "") >= cutoff:
            continue
        version = Version(name.split("-")[1])
        if version.is_prerelease or version.is_devrelease:
            continue
        required = item.get("requires-python")
        if required and not SpecifierSet(required).contains(python):
            continue
        if best is None or version > best:
            best = version
    return str(best) if best else None


def choose_module(project, names):
    """Prefer the import name that matches the project, then the first public one."""
    expected = re.sub(r"[-_.]+", "_", project).lower()
    if project in MODULES:
        return MODULES[project]
    if expected in names:
        return expected
    public = [name for name in names if not name.startswith("_")]
    return (public or names)[0] if names else None


def detect_modules(project, version, executable, root, pip):
    with tempfile.TemporaryDirectory(prefix=f"{project}-", dir=root) as temporary:
        working = Path(temporary)
        prefix = working / "prefix"
        installation = package_bench.launch(
            executable, working, "-c", package_bench.START_PIP, str(pip),
            *package_bench.install_arguments(prefix, "cpython"), f"{project}=={version}", timeout=180)
        if installation.returncode:
            raise RuntimeError(package_bench.diagnostic(installation, root))
        found = package_bench.launch(
            executable, working, "-c", FIND_MODULES, os.pathsep.join(package_bench.site_directories(prefix)),
            project, timeout=30)
        return json.loads(found.stdout.splitlines()[-1])


# The ranking is resolved for the Python version of the interpreter running this
# script, which also installs each release to find its module.
PYTHON = f"{sys.version_info.major}.{sys.version_info.minor}"


def resolve(entry, cutoff, executable, root, pip):
    project = entry["project"]
    version = choose_version(release_files(project), cutoff, PYTHON)
    if version is None:
        raise RuntimeError(f"{project}: no stable wheel for Python {PYTHON} before {cutoff}")
    module = choose_module(project, detect_modules(project, version, executable, root, pip))
    return {**entry, "version": version, "module": module}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(), help="First day left out of the window")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", type=Path, help="Defaults to the ranking of this interpreter's Python version")
    arguments = parser.parse_args()
    if arguments.output is None:
        if PYTHON not in REFERENCES:
            parser.error(f"Python {PYTHON} is not a measured version. Run this script with one of {', '.join(REFERENCES)}.")
        arguments.output = REFERENCES[PYTHON].ranking
    start = arguments.end - timedelta(days=arguments.days)
    query, projects = ranking(start, arguments.end, arguments.limit)
    with tempfile.TemporaryDirectory(prefix="update-ranking-") as temporary:
        root = Path(temporary)
        pip = prepare((package_bench.PIP,), root / "installer")
        with ThreadPoolExecutor(max_workers=4) as executor:
            items = list(executor.map(
                lambda entry: resolve(entry, arguments.end.isoformat(), sys.executable, root, pip), projects))
    document = {"start": start.isoformat(), "end": arguments.end.isoformat(),
                "source": "https://github.com/ClickHouse/clickpy", "query": query, "items": items}
    arguments.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} projects, {start} to {arguments.end - timedelta(days=1)}")


if __name__ == "__main__":
    main()
