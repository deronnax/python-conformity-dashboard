"""Generate the bilingual static dashboard from a measurement report."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote

from dashboard_content import TRANSLATIONS


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "site"
VIEWS = {"packages": "pypi-packages", "applications": "applications", "common": "shared-cases", "upstream": "cpython-tests"}
OBSERVED_VALUE = re.compile(r"([A-Za-z_]\w*): (.*)")


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


def render_summaries(rows, runtimes, copy, label_key="passedOn"):
    cards = []
    for runtime in runtimes:
        counts = Counter(row["outcomes"][runtime["id"]]["status"] for row in rows)
        passed = counts["passed"]
        version = runtime["version"]
        build = version.split()[0]
        named = re.search(r"(?:PyPy|RustPython) v?([\d.]+)", version, flags=re.IGNORECASE)
        if named and runtime["id"] != "cpython":
            build = named[1]
        name = runtime["name"]
        label = copy[label_key].format(runtime=name)
        breakdown = " · ".join(
            f"{counts[status]} {singular if counts[status] == 1 else plural}"
            for status, (singular, plural) in copy["totals"].items() if counts[status]
        )
        detail = f'<p class="summary-detail">{escape(breakdown)}</p>' if breakdown else ""
        cards.append(f"""<article class="summary-card">
            <p class="runtime-name" title="{escape(version)}">{escape(name)} {escape(build)}</p>
            <p class="score">{passed} / {len(rows)}</p>
            <progress max="{len(rows)}" value="{passed}" aria-label="{escape(label)}"></progress>{detail}
          </article>""")
    return "".join(cards)


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
    if row["source"].startswith("https://"):
        contents.append(
            f'<a href="{escape(row["source"])}" title="{escape(row["sourceTest"])}">{escape(copy["source"])}</a>'
        )
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
        table_rows.append(f'<tr data-module="{escape(row["module"])}"{flag}>{"".join(cells)}</tr>')

    modules = sorted({row["module"] for row in rows})
    options = [f'<option value="">{escape(copy["allModules"])}</option>']
    options.extend(f'<option value="{escape(module)}">{escape(module)}</option>' for module in modules)
    return f"""<section id="{VIEWS[suite]}" data-dashboard-panel data-comparison>
        <h2>{escape(copy[suite + "Tab"])}</h2>
        <p class="description">{escape(copy["descriptions"][suite])}</p>
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy)}
        </div>
        <div class="filters" hidden>
          <label>{escape(copy["module"])} <select data-module-filter>{"".join(options)}</select></label>
          <label class="only-differences">
            <input type="checkbox" data-difference-filter> {escape(copy["onlyDifferences"])}
          </label>
          <span class="case-count" role="status" data-case-count data-unit="{escape(copy["caseUnit"])}">
            {len(rows)} / {len(rows)} {escape(copy["caseUnit"])}
          </span>
        </div>
        <div class="table-scroll" role="region" aria-label="{escape(copy["caseTable"])}" tabindex="0">
          <table>
            {table_head((copy["case"],), runtimes)}
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
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy, "applicationsPassedOn")}
        </div>
        <div class="table-scroll" role="region" aria-label="{escape(copy["applicationsTab"])}" tabindex="0">
          <table class="result-table">
            {table_head((copy["scenario"],), runtimes)}
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
    return f"""<section id="{VIEWS["packages"]}" data-dashboard-panel>
        {heading}
        <p class="description">{escape(window)} · <a href="{escape(ranking["source"])}">ClickPy</a></p>
        <p class="description">{escape(copy["packagesMethod"])}</p>
        <div class="summaries" aria-label="{escape(copy["summaries"])}">
          {render_summaries(rows, runtimes, copy, "packagesPassedOn")}
        </div>
        <div class="table-scroll package-results" role="region" aria-label="{escape(copy["packagesTitle"])}" tabindex="0">
          <table class="package-table">
            {table_head(labels, runtimes, classes=("column-rank", "", "column-downloads"), notes=abis)}
            <tbody>{"".join(listing)}</tbody>
          </table>
        </div>
      </section>"""


def render_page(report, language, template, assets):
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
        common=render_comparison("common", report, language, copy),
        upstream=render_comparison("upstream", report, language, copy),
        scriptVersion=hashlib.sha256(assets["dashboard.js"]).hexdigest()[:12],
        styleVersion=hashlib.sha256(assets["styles.css"]).hexdigest()[:12],
    )


def generate(report, output):
    french = output / "fr"
    french.mkdir(parents=True, exist_ok=True)
    template = Template((ASSETS / "index.html").read_text(encoding="utf-8"))
    assets = {name: (ASSETS / name).read_bytes() for name in ("dashboard.js", "styles.css")}
    for directory, language in ((output, "en"), (french, "fr")):
        (directory / "index.html").write_text(render_page(report, language, template, assets), encoding="utf-8")
    (output / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
    for name, contents in assets.items():
        (output / name).write_bytes(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    arguments = parser.parse_args()
    generate(json.loads(arguments.report.read_text(encoding="utf-8")), arguments.output)


if __name__ == "__main__":
    main()
