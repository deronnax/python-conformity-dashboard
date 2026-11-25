"""Generate the bilingual static dashboard from a measurement report."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from math import ceil, floor, log10
from pathlib import Path
from string import Template
from urllib.parse import quote

from dashboard_content import TRANSLATIONS
from history import dump as dump_history, load as load_history, merge, snapshot
from performance import geometric_means, speedup


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "site"
VIEWS = {"packages": "pypi-packages", "applications": "applications", "common": "shared-cases",
         "upstream": "cpython-tests", "interpreters": "interpreters", "performance": "performance",
         "history": "history"}
OBSERVED_VALUE = re.compile(r"([A-Za-z_]\w*): (.*)")


def language_version(runtime):
    """Python version an interpreter implements, as opposed to its own release number."""
    return runtime.get("language") or runtime["version"].split()[0]


def implementation_version(runtime):
    if runtime.get("implementationVersion"):
        return runtime["implementationVersion"]
    version = runtime["version"]
    named = re.search(r"(?:PyPy|RustPython) v?([\d.]+)", version, flags=re.IGNORECASE)
    return named[1] if named and runtime["id"] != "cpython" else version.split()[0]


def minor(version):
    return ".".join(version.split(".")[:2])


def cross_version(runtime, reference):
    return minor(language_version(runtime)) != minor(reference)


def version_notes(runtimes, reference, copy):
    """Column notes for interpreters that implement another Python version than the reference."""
    return {runtime["id"]: copy["crossVersionNote"].format(version=minor(language_version(runtime)))
            for runtime in runtimes if cross_version(runtime, reference)}


def visible_runtimes(rows, runtimes):
    return [runtime for runtime in runtimes if any(runtime["id"] in row["outcomes"] for row in rows)]


def css_class(name):
    return f' class="{escape(name)}"' if name else ""


def table_head(labels, runtimes, *, classes=(), notes=None):
    notes = notes or {}
    classes = tuple(classes) + ("",) * (len(labels) - len(classes))
    columns = [f'<th scope="col"{css_class(name)}>{escape(label)}</th>' for label, name in zip(labels, classes)]
    for runtime in runtimes:
        note = notes.get(runtime["id"])
        extra = f'<span class="runtime-note">{escape(note)}</span>' if note else ""
        columns.append(f'<th scope="col" title="{escape(runtime["version"])}">{escape(runtime["name"])}{extra}</th>')
    return "<thead><tr>" + "".join(columns) + "</tr></thead>"


def badge(outcome, copy):
    status = outcome["status"]
    return f'<span class="status {escape(status)}">{escape(copy["statuses"][status])}</span>'


def outcome_detail(outcome, language):
    return outcome.get("detailFr", outcome["detail"]) if language == "fr" else outcome["detail"]


def describe_observation(outcome, language, copy):
    """Phrase a shared-case observation such as "int: 6" or "exception: ValueError"."""
    text = outcome["detail"]
    if outcome["status"] not in ("passed", "different") or "\n" in text:
        return outcome_detail(outcome, language)
    phrases = copy["observations"]
    if text.startswith("unexpected exception: "):
        return phrases["unexpected"].format(exception=text.removeprefix("unexpected exception: "))
    if text.startswith("exception: "):
        return phrases["raises"].format(exception=text.removeprefix("exception: "))
    match = OBSERVED_VALUE.fullmatch(text)
    if not match:
        return outcome_detail(outcome, language)
    if match[1] == "NoneType":
        return phrases["returnsNone"]
    return phrases["returns"].format(value=match[2], type=match[1])


def detailed_badge(outcome, language, copy):
    detail = outcome_detail(outcome, language)
    label = badge(outcome, copy)
    if detail:
        return f'<details class="package-detail"><summary>{label}</summary><pre>{escape(detail)}</pre></details>'
    return label


def render_summaries(rows, runtimes, copy, label_key="passedOn", reference=None):
    cards = []
    for runtime in runtimes:
        counts = Counter(row["outcomes"][runtime["id"]]["status"] for row in rows)
        passed = counts["passed"]
        version = runtime["version"]
        build = implementation_version(runtime)
        name = runtime["name"]
        label = copy[label_key].format(runtime=name)
        breakdown = " · ".join(
            f"{counts[status]} {singular if counts[status] == 1 else plural}"
            for status, (singular, plural) in copy["totals"].items() if counts[status]
        )
        detail = f'<p class="summary-detail">{escape(breakdown)}</p>' if breakdown else ""
        if reference and cross_version(runtime, reference):
            note = copy["crossVersionCard"].format(version=language_version(runtime), reference=reference)
            detail = f'<p class="summary-detail cross-version">{escape(note)}</p>' + detail
        cards.append(f"""<article class="summary-card">
            <p class="runtime-name" title="{escape(version)}">{escape(name)} {escape(build)}</p>
            <p class="score">{passed} / {len(rows)}</p>
            <progress max="{len(rows)}" value="{passed}" aria-label="{escape(label)}"></progress>{detail}
          </article>""")
    return "".join(cards)


def contract_line(row, copy):
    """Say what guarantees the expected result, linked to the documentation that states it."""
    kind = row["contract"]
    label = escape(copy["contracts"].get(kind, kind))
    if row.get("contractSource"):
        label = f'<a href="{escape(row["contractSource"])}">{label}</a>'
    prefix, _, suffix = copy["contractLine"].partition("{contract}")
    return f'<p class="contract">{escape(prefix)}{label}{escape(suffix)}</p>'


def case_details(row, runtimes, language, copy, *, observed):
    api = row.get("api")
    title = row.get("titleFr", row["title"]) if language == "fr" else row["title"]
    label, description = (api, title) if api else (title, row["module"])
    details = [
        f"<summary><code>{escape(label)}</code><span class=\"case-title\">{escape(description)}</span></summary>"
    ]
    contents = []
    if row.get("code"):
        contents.append(f'<pre>{escape(row["code"])}</pre>')
    if row.get("contract"):
        contents.append(contract_line(row, copy))
    if (row.get("source") or "").startswith("https://"):
        label = copy["upstreamSame"] if observed else copy["source"]
        contents.append(
            f'<p class="provenance"><a href="{escape(row["source"])}" title="{escape(row["sourceTest"])}">{escape(label)}</a></p>'
        )
    elif observed:
        contents.append(f'<p class="provenance">{escape(copy["upstreamNone"])}</p>')
    for runtime in runtimes:
        outcome = row["outcomes"][runtime["id"]]
        detail = describe_observation(outcome, language, copy) if observed else outcome_detail(outcome, language)
        if detail:
            contents.append(f'<p class="detail-runtime">{escape(runtime["name"])}</p><pre>{escape(detail)}</pre>')
    details.append('<div class="case-detail">' + "".join(contents) + "</div>")
    return "<details>" + "".join(details) + "</details>"


def render_comparison(suite, report, language, copy):
    rows = report[suite]
    runtimes = visible_runtimes(rows, report["runtimes"])
    table_rows = []
    for row in rows:
        difference = any(outcome["status"] != "passed" for outcome in row["outcomes"].values())
        details = case_details(row, runtimes, language, copy, observed=suite == "common")
        cells = [f'<th scope="row">{details}</th>']
        cells.extend(f'<td>{badge(row["outcomes"][runtime["id"]], copy)}</td>' for runtime in runtimes)
        flag = " data-difference" if difference else ""
        if row.get("contract"):
            flag += f' data-contract="{escape(row["contract"])}"'
        table_rows.append(f'<tr data-module="{escape(row["module"])}"{flag}>{"".join(cells)}</tr>')

    modules = sorted({row["module"] for row in rows})
    options = [f'<option value="">{escape(copy["allModules"])}</option>']
    options.extend(f'<option value="{escape(module)}">{escape(module)}</option>' for module in modules)
    contracts = Counter(row["contract"] for row in rows if row.get("contract"))
    contract_filter = contract_summary = ""
    if contracts:
        kinds = [kind for kind in copy["contracts"] if contracts[kind]]
        choices = [f'<option value="">{escape(copy["allContracts"])}</option>']
        choices.extend(f'<option value="{escape(kind)}">{escape(copy["contracts"][kind])} ({contracts[kind]})</option>'
                       for kind in kinds)
        contract_filter = (f'<label>{escape(copy["contract"])} <select data-contract-filter>'
                           f'{"".join(choices)}</select></label>')
        contract_summary = f'<p class="description">{escape(copy["contractIntro"])}</p>'
    return f"""<section id="{VIEWS[suite]}" data-dashboard-panel data-comparison>
        <h2>{escape(copy[suite + "Tab"])}</h2>
        <p class="description">{escape(copy["descriptions"][suite])}</p>
        <p class="description">{escape(copy["performanceOnly"])}</p>
        {contract_summary}
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy, reference=report["reference"])}
        </div>
        <div class="filters" hidden>
          <label>{escape(copy["module"])} <select data-module-filter>{"".join(options)}</select></label>
          {contract_filter}
          <label class="only-differences">
            <input type="checkbox" data-difference-filter> {escape(copy["onlyDifferences"])}
          </label>
          <span class="case-count" role="status" data-case-count data-unit="{escape(copy["caseUnit"])}">
            {len(rows)} / {len(rows)} {escape(copy["caseUnit"])}
          </span>
        </div>
        <div class="table-scroll" role="region" aria-label="{escape(copy["caseTable"])}" tabindex="0">
          <table>
            {table_head((copy["case"],), runtimes, notes=version_notes(runtimes, report["reference"], copy))}
            <tbody>
              {"".join(table_rows)}
              <tr data-empty hidden><td class="empty" colspan="{len(runtimes) + 1}"
                data-filtered="{escape(copy["empty"])}" data-differences="{escape(copy["noDifferences"])}">{escape(copy["empty"])}</td></tr>
            </tbody>
          </table>
        </div>
      </section>"""


def render_applications(report, language, copy):
    heading = f'<h2>{escape(copy["applicationsTab"])}</h2>'
    rows = report.get("applications") or []
    if not rows:
        return (
            f'<section id="{VIEWS["applications"]}" data-dashboard-panel>'
            f'{heading}<p class="description">{escape(copy["applicationsEmpty"])}</p></section>'
        )
    runtimes = visible_runtimes(rows, report["runtimes"])
    listing = []
    for row in rows:
        title = copy["applicationTitles"].get(row["id"], row["id"])
        cells = [
            f'<th scope="row"><strong>{escape(row["package"])}</strong> {escape(row["version"])}'
            f'<span class="scenario-title">{escape(title)}</span></th>'
        ]
        cells.extend(f'<td>{detailed_badge(row["outcomes"][runtime["id"]], language, copy)}</td>' for runtime in runtimes)
        listing.append("<tr>" + "".join(cells) + "</tr>")
    return f"""<section id="{VIEWS["applications"]}" data-dashboard-panel>
        {heading}
        <p class="description">{escape(copy["descriptions"]["applications"])}</p>
        <p class="description">{escape(copy["performanceOnly"])}</p>
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy, "applicationsPassedOn", report["reference"])}
        </div>
        <div class="table-scroll" role="region" aria-label="{escape(copy["applicationsTab"])}" tabindex="0">
          <table class="result-table">
            {table_head((copy["scenario"],), runtimes, notes=version_notes(runtimes, report["reference"], copy))}
            <tbody>{"".join(listing)}</tbody>
          </table>
        </div>
      </section>"""


def render_packages(report, language, copy):
    heading = f'<h2>{escape(copy["packagesTitle"])}</h2>'
    ranking = report.get("packages")
    if not ranking:
        return (
            f'<section id="{VIEWS["packages"]}" data-dashboard-panel>'
            f'{heading}<p>{escape(copy["packagesEmpty"])}</p></section>'
        )
    rows = ranking["items"]
    runtimes = visible_runtimes(rows, report["runtimes"])
    listing = []
    for number, row in enumerate(rows, 1):
        project, version, module = row["project"], row["version"], row["module"]
        url = f"https://pypi.org/project/{quote(project, safe='')}/{quote(version, safe='')}/"
        downloads = format(row["downloads"], ",")
        if language == "fr":
            downloads = downloads.replace(",", "\u202f")
        cells = [
            f'<td class="column-rank">{number}</td>',
            f'<th scope="row"><a href="{escape(url)}">{escape(project)}</a> {escape(version)}'
            f'<code class="package-module">{escape(module)}</code></th>',
            f'<td class="column-downloads">{escape(downloads)}</td>',
        ]
        cells.extend(f'<td>{detailed_badge(row["outcomes"][runtime["id"]], language, copy)}</td>' for runtime in runtimes)
        listing.append("<tr>" + "".join(cells) + "</tr>")
    last_date = date.fromisoformat(ranking["end"]) - timedelta(days=1)
    window = copy["packagesWindow"].format(start=ranking["start"], end=last_date)
    labels = (copy["rank"], copy["package"], copy["downloads"])
    abis = {runtime: tag["abi"] for runtime, tag in ranking.get("tags", {}).items()}
    for runtime, note in version_notes(runtimes, report["reference"], copy).items():
        abis[runtime] = f"{abis[runtime]} · {note}" if runtime in abis else note
    return f"""<section id="{VIEWS["packages"]}" data-dashboard-panel>
        {heading}
        <p class="description">{escape(window)} · <a href="{escape(ranking["source"])}">ClickPy</a></p>
        <p class="description">{escape(copy["packagesMethod"])}</p>
        <p class="description">{escape(copy["performanceOnly"])}</p>
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy, "packagesPassedOn", report["reference"])}
        </div>
        <div class="table-scroll package-results" role="region" aria-label="{escape(copy["packagesTitle"])}" tabindex="0">
          <table class="package-table">
            {table_head(labels, runtimes, classes=("column-rank", "", "column-downloads"), notes=abis)}
            <tbody>{"".join(listing)}</tbody>
          </table>
        </div>
      </section>"""


def render_interpreters(report, language, copy):
    runtimes = report["runtimes"]
    tags = (report.get("packages") or {}).get("tags") or {}
    listing = []
    for runtime in runtimes:
        threads = runtime.get("threads") or {}
        if "speedup" in threads:
            gil = {True: "gilEnabled", False: "gilDisabled", None: "gilUnknown"}[threads.get("gil")]
            detail = copy["threadsDetail"].format(workers=threads["workers"], cores=threads["cores"])
            speedup = (
                f'<progress max="{threads["workers"]}" value="{threads["speedup"]}" '
                f'aria-label="{escape(copy["threadsSpeedup"])}"></progress>'
                f'<span class="speedup"><strong>×{threads["speedup"]:g}</strong> · {escape(detail)}</span>'
            )
            gil_cell = escape(copy[gil])
        elif threads:
            gil_cell, speedup = escape(copy["gilUnknown"]), badge(threads, copy)
        else:
            gil_cell, speedup = escape(copy["gilUnknown"]), ""
        language = language_version(runtime)
        if cross_version(runtime, report["reference"]):
            note = copy["otherVersion"].format(reference=report["reference"])
            language_cell = f'{escape(language)}<span class="version-note">{escape(note)}</span>'
        else:
            language_cell = escape(language)
        abi = tags.get(runtime["id"], {}).get("abi")
        listing.append(
            f'<tr><th scope="row"><span class="runtime-key series-{css_token(runtime["id"])}" aria-hidden="true"></span>'
            f'{escape(runtime["name"])}</th><td title="{escape(runtime["version"])}">{escape(implementation_version(runtime))}</td>'
            f'<td>{language_cell}</td>'
            f'<td>{"<code>" + escape(abi) + "</code>" if abi else ""}</td><td>{gil_cell}</td><td class="speedup-cell">{speedup}</td></tr>'
        )
    labels = (copy["interpreter"], copy["implementationVersion"], copy["pythonVersion"], copy["abi"], copy["gil"],
              copy["threadsSpeedup"])
    head = "<thead><tr>" + "".join(f'<th scope="col">{escape(label)}</th>' for label in labels) + "</tr></thead>"
    return f"""<section id="{VIEWS["interpreters"]}" data-dashboard-panel>
        <h2>{escape(copy["interpretersTab"])}</h2>
        <p class="description">{escape(copy["interpretersMethod"])}</p>
        <div class="table-scroll" role="region" aria-label="{escape(copy["interpretersTab"])}" tabindex="0">
          <table class="interpreter-table">
            {head}
            <tbody>{"".join(listing)}</tbody>
          </table>
        </div>
      </section>"""


def number(value, language, digits=3):
    text = f"{value:.{digits}g}"
    if "e" in text:
        text = f"{value:f}".rstrip("0").rstrip(".")
    return text.replace(".", ",") if language == "fr" else text


def ratio_text(ratio, language, copy):
    if 0.95 <= ratio <= 1.05:
        return copy["performanceSame"]
    factor = ratio if ratio > 1 else 1 / ratio
    text = f"{factor:.1f}" if factor < 10 else f"{factor:.0f}"
    key = "performanceFaster" if ratio > 1 else "performanceSlower"
    return copy[key].format(ratio=text.replace(".", ",") if language == "fr" else text)


def benchmark_cell(row, runtime, language, copy):
    outcome = row["outcomes"][runtime["id"]]
    if outcome["status"] != "passed":
        return detailed_badge(outcome, language, copy)
    seconds = copy["performanceSeconds"].format(value=number(outcome["median"], language))
    detail = copy["performanceDetail"].format(
        median=number(outcome["median"], language), min=number(outcome["min"], language),
        stdev=number(outcome["stdev"], language), rounds=outcome["rounds"], first=number(outcome["first"], language))
    if runtime["id"] == "cpython":
        comparison = copy["performanceReference"]
        tone = "same"
    else:
        ratio = speedup(row, runtime["id"])
        comparison = ratio_text(ratio, language, copy)
        tone = "same" if 0.95 <= ratio <= 1.05 else ("faster" if ratio > 1 else "slower")
    return (f'<details class="package-detail"><summary><span class="time">{escape(seconds)}</span>'
            f'<span class="ratio {tone}">{escape(comparison)}</span></summary><pre>{escape(detail)}</pre></details>')


def render_benchmarks(report, language, copy):
    heading = f'<h2>{escape(copy["performanceTab"])}</h2>'
    rows = report.get("benchmarks") or []
    if not rows:
        return (f'<section id="{VIEWS["performance"]}" data-dashboard-panel>'
                f'{heading}<p class="description">{escape(copy["performanceEmpty"])}</p></section>')
    runtimes = visible_runtimes(rows, report["runtimes"])
    means = geometric_means(rows, [runtime["id"] for runtime in runtimes])
    cards = []
    for runtime in runtimes:
        mean = means.get(runtime["id"])
        if runtime["id"] == "cpython":
            score, detail = "×1", copy["performanceReference"]
        elif mean:
            score = "×" + number(mean[0], language, 2)
            detail = copy["performanceAll"] if mean[1] == len(rows) else copy["performanceMeanDetail"].format(
                count=mean[1], total=len(rows))
        else:
            score, detail = "–", ""
        build = runtime["version"].split()[0]
        cards.append(f"""<article class="summary-card">
            <p class="runtime-name" title="{escape(runtime["version"])}">{escape(runtime["name"])} {escape(build)}</p>
            <p class="score">{escape(score)}</p><p class="summary-detail">{escape(detail)}</p>
          </article>""")
    listing = []
    for row in rows:
        title = row.get("titleFr", row["title"]) if language == "fr" else row["title"]
        cells = "".join(f"<td>{benchmark_cell(row, runtime, language, copy)}</td>" for runtime in runtimes)
        listing.append(f'<tr><th scope="row"><code>{escape(row["id"])}</code>'
                       f'<span class="scenario-title">{escape(title)}</span></th>{cells}</tr>')
    return f"""<section id="{VIEWS["performance"]}" data-dashboard-panel>
        {heading}
        <p class="description">{escape(copy["performanceMethod"])}</p>
        <h3 class="subheading">{escape(copy["performanceMean"])}</h3>
        <div class="summaries" aria-label="{escape(copy["summaries"])}">{"".join(cards)}</div>
        <div class="table-scroll" role="region" aria-label="{escape(copy["performanceTab"])}" tabindex="0">
          <table class="result-table">
            {table_head((copy["performanceBenchmark"],), runtimes)}
            <tbody>{"".join(listing)}</tbody>
          </table>
        </div>
      </section>"""


def css_token(value):
    return re.sub(r"[^a-z0-9-]", "", str(value).lower())


def history_series(entries, chart):
    """Return {runtime id: (name, [(timestamp, value, label)])} and the top of the scale."""
    series = {}
    top = 0
    for entry in entries:
        moment = entry["generatedAt"]
        if chart == "threads":
            points = {key: item for key, item in entry["runtimes"].items() if item.get("speedup") is not None}
            top = max([top, *(item.get("workers") or 0 for item in points.values())])
            for key, item in points.items():
                label = f'×{item["speedup"]:g}'
                series.setdefault(key, (item["name"], []))[1].append((moment, item["speedup"], label))
        elif chart == "performance":
            for key, item in entry["runtimes"].items():
                if item.get("speed"):
                    label = f'×{item["speed"]:.2g}'
                    series.setdefault(key, (item["name"], []))[1].append((moment, item["speed"], label))
                    top = max(top, item["speed"])
        elif chart in entry["suites"]:
            suite = entry["suites"][chart]
            top = max(top, suite["total"])
            for key, counts in suite["runtimes"].items():
                passed = counts.get("passed", 0)
                name = entry["runtimes"].get(key, {}).get("name", key)
                series.setdefault(key, (name, []))[1].append((moment, passed, f'{passed} / {suite["total"]}'))
    return series, top


def chart_scale(series, top, chart):
    """Return the tick list and the function that maps a value to a height fraction (0 bottom, 1 top)."""
    if chart == "performance":
        values = [value for _, points in series.values() for _, value, _ in points]
        low, high = floor(log10(min(values))), ceil(log10(max(values)))
        high = max(high, low + 1)
        ticks = [(10 ** power, f"×{10 ** power:g}") for power in range(low, high + 1)]
        return ticks, lambda value: (log10(value) - low) / (high - low)
    if chart == "threads":
        return [(tick, f"×{tick}") for tick in range(int(top) + 1)], lambda value: value / top
    return [(tick, str(tick)) for tick in sorted({0, top // 2, top})], lambda value: value / top


def render_chart(entries, chart, copy):
    series, top = history_series(entries, chart)
    if not series or not top:
        return ""
    width, height, left, right, upper, lower = 640, 250, 44, 16, 14, 34
    moments = sorted({moment for _, points in series.values() for moment, _, _ in points})
    times = [datetime.fromisoformat(moment).timestamp() for moment in moments]
    span = times[-1] - times[0]

    def x(moment):
        if not span:
            return left + (width - left - right) / 2
        return left + (datetime.fromisoformat(moment).timestamp() - times[0]) / span * (width - left - right)

    ticks, fraction = chart_scale(series, top, chart)

    def y(value):
        return upper + (1 - fraction(value)) * (height - upper - lower)

    parts = []
    for tick, label in ticks:
        parts.append(f'<line class="grid" x1="{left}" x2="{width - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>'
                     f'<text class="axis" x="{left - 8}" y="{y(tick) + 4:.1f}" text-anchor="end">{label}</text>')
    shown = moments if len(moments) <= 4 else [moments[0], moments[len(moments) // 3], moments[2 * len(moments) // 3], moments[-1]]
    for moment in shown:
        anchor = "middle" if 0 < moments.index(moment) < len(moments) - 1 or len(moments) == 1 else (
            "start" if moment == moments[0] else "end")
        parts.append(f'<text class="axis" x="{x(moment):.1f}" y="{height - 10}" text-anchor="{anchor}">{escape(moment[:10])}</text>')
    for key, (name, points) in series.items():
        token = css_token(key)
        if len(points) > 1:
            path = " ".join(f"{x(moment):.1f},{y(value):.1f}" for moment, value, _ in points)
            parts.append(f'<polyline class="line series-{token}" points="{path}"/>')
        parts.extend(f'<circle class="marker series-{token}" cx="{x(moment):.1f}" cy="{y(value):.1f}" r="4"/>'
                     for moment, value, _ in points)
    band = max(24, (width - left - right) / max(len(moments), 1))
    parts.append(f'<line class="crosshair" y1="{upper}" y2="{height - lower}" hidden/>')
    for moment in moments:
        readout = [[series[key][0], dict((m, label) for m, _, label in series[key][1])[moment], css_token(key)]
                   for key in series if moment in {m for m, _, _ in series[key][1]}]
        parts.append(
            f'<rect class="hit" tabindex="0" x="{x(moment) - band / 2:.1f}" y="{upper}" width="{band:.1f}" '
            f'height="{height - upper - lower}" data-x="{x(moment):.1f}" data-date="{escape(moment[:10])}" '
            f'data-readout="{escape(json.dumps(readout, ensure_ascii=False))}"/>')
    title = copy["historyCharts"][chart]
    legend = "".join(f'<li><span class="key series-{css_token(key)}"></span>{escape(name)}</li>'
                     for key, (name, _) in series.items())
    columns = "".join(f'<th scope="col">{escape(name)}</th>' for name, _ in series.values())
    body = []
    for moment in moments:
        cells = "".join(
            f"<td>{escape(dict((m, label) for m, _, label in points).get(moment, ''))}</td>"
            for _, points in series.values())
        body.append(f'<tr><th scope="row">{escape(moment[:10])}</th>{cells}</tr>')
    return f"""<figure class="chart" data-chart>
          <figcaption>{escape(title)}</figcaption>
          <ul class="legend">{legend}</ul>
          <svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">{"".join(parts)}</svg>
          <div class="tooltip" role="status" hidden></div>
          <details class="chart-table"><summary>{escape(copy["historyTable"])}</summary>
            <div class="table-scroll"><table><thead><tr><th scope="col">{escape(copy["historyDate"])}</th>{columns}</tr></thead>
            <tbody>{"".join(body)}</tbody></table></div>
          </details>
        </figure>"""


def render_history(entries, copy):
    charts = "".join(render_chart(entries, chart, copy)
                     for chart in ("packages", "applications", "common", "performance", "threads"))
    first = f'<p class="description">{escape(copy["historyFirst"])}</p>' if len(entries) < 2 else ""
    return f"""<section id="{VIEWS["history"]}" data-dashboard-panel>
        <h2>{escape(copy["historyTab"])}</h2>
        <p class="description">{escape(copy["historyIntro"])}</p>
        {first}
        <div class="charts">{charts}</div>
      </section>"""


def render_page(report, language, template, assets, history):
    copy = TRANSLATIONS[language]
    base = "../" if language == "fr" else ""
    french_page = "index.html" if language == "fr" else "fr/index.html"
    generated = report["generatedAt"]
    stamp = datetime.fromisoformat(generated).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fields = {key: escape(value) for key, value in copy.items() if isinstance(value, str)}
    return template.substitute(
        fields,
        lang=language,
        base=base,
        frenchPage=french_page,
        englishCurrent=' aria-current="page"' if language == "en" else "",
        frenchCurrent=' aria-current="page"' if language == "fr" else "",
        generatedAt=escape(generated),
        timestamp=escape(stamp),
        platform=escape(report["platform"]),
        referenceVersion=escape(report["reference"]),
        packages=render_packages(report, language, copy),
        applications=render_applications(report, language, copy),
        interpreters=render_interpreters(report, language, copy),
        performance=render_benchmarks(report, language, copy),
        history=render_history(history, copy),
        common=render_comparison("common", report, language, copy),
        upstream=render_comparison("upstream", report, language, copy),
        scriptVersion=hashlib.sha256(assets["dashboard.js"]).hexdigest()[:12],
        styleVersion=hashlib.sha256(assets["styles.css"]).hexdigest()[:12],
    )


def generate(report, output, previous_history=()):
    history = merge(list(previous_history), snapshot(report))
    french = output / "fr"
    french.mkdir(parents=True, exist_ok=True)
    template = Template((ASSETS / "index.html").read_text(encoding="utf-8"))
    assets = {name: (ASSETS / name).read_bytes() for name in ("dashboard.js", "styles.css")}
    for directory, language in ((output, "en"), (french, "fr")):
        (directory / "index.html").write_text(render_page(report, language, template, assets, history), encoding="utf-8")
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "history.json").write_text(dump_history(history), encoding="utf-8")
    (output / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
    for name, contents in assets.items():
        (output / name).write_bytes(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--history", type=Path, help="history.json from an earlier run, extended with this report")
    arguments = parser.parse_args()
    previous = load_history(arguments.history) if arguments.history else []
    generate(json.loads(arguments.report.read_text(encoding="utf-8")), arguments.output, previous)


if __name__ == "__main__":
    main()
