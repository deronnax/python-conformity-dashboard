"""Keep one compact snapshot per measurement run so the dashboard can show trends.

GitHub Pages replaces the whole site on every deployment, so the workflow
downloads the published history.json, adds the new snapshot and publishes it
again. A run only ever appends: the file is never rebuilt from other sources.
"""

import json
from collections import Counter
from pathlib import Path


VERSION = 1
LIMIT = 520  # about ten years of weekly runs
SUITES = ("packages", "applications", "common", "upstream")


def rows(report, suite):
    if suite == "packages":
        return (report.get("packages") or {}).get("items") or []
    return report.get(suite) or []


def snapshot(report):
    """Summarize a report as status counts per suite and runtime, plus thread scaling."""
    suites = {}
    for suite in SUITES:
        listing = rows(report, suite)
        if not listing:
            continue
        counts = {}
        for runtime in report["runtimes"]:
            outcomes = [row["outcomes"][runtime["id"]]["status"] for row in listing if runtime["id"] in row["outcomes"]]
            if outcomes:
                counts[runtime["id"]] = dict(sorted(Counter(outcomes).items()))
        suites[suite] = {"total": len(listing), "runtimes": counts}
    runtimes = {}
    for runtime in report["runtimes"]:
        threads = runtime.get("threads") or {}
        runtimes[runtime["id"]] = {
            "name": runtime["name"],
            "build": runtime["version"].split()[0],
            "speedup": threads.get("speedup"),
            "workers": threads.get("workers"),
            "cores": threads.get("cores"),
        }
    return {"generatedAt": report["generatedAt"], "reference": report["reference"], "runtimes": runtimes, "suites": suites}


def merge(previous, entry):
    """Append a snapshot to earlier ones, replacing an entry from the same run."""
    kept = [item for item in previous if item.get("generatedAt") != entry["generatedAt"]]
    kept.append(entry)
    kept.sort(key=lambda item: item["generatedAt"])
    return kept[-LIMIT:]


def load(path):
    """Read earlier snapshots. A missing or unreadable file starts a new history."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(document, dict) or document.get("version") != VERSION:
        return []
    return [item for item in document.get("entries") or [] if isinstance(item, dict) and "generatedAt" in item]


def dump(entries):
    return json.dumps({"version": VERSION, "entries": entries}, indent=1, ensure_ascii=False) + "\n"
