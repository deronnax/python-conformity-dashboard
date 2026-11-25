"""Generate the bilingual static dashboard from a measurement report."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from string import Template

from dashboard_content import TRANSLATIONS, USE_CASES


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "site"
VIEWS = {"uses": "use-cases", "common": "shared-cases", "upstream": "cpython-tests"}


def visible_runtimes(rows, runtimes):
    return [runtime for runtime in runtimes if any(runtime["id"] in row["outcomes"] for row in rows)]


def table_head(label, runtimes):
    columns = [f'<th scope="col">{escape(label)}</th>']
    for runtime in runtimes:
        columns.append(f'<th scope="col" title="{escape(runtime["version"])}">{escape(runtime["name"])}</th>')
    return "<thead><tr>" + "".join(columns) + "</tr></thead>"


def badge(outcome, copy):
    status = outcome["status"]
    label = copy["noWheel"] if status == "noWheel" else copy["statuses"][status]
    return f'<span class="status {escape(status)}">{escape(label)}</span>'


def outcome_detail(outcome, language):
    return outcome.get("detailFr", outcome["detail"]) if language == "fr" else outcome["detail"]


def render_summaries(rows, runtimes, copy):
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
        label = copy["passedOn"].format(runtime=name)
        breakdown = " · ".join(
            f"{counts[status]} {singular if counts[status] == 1 else plural}"
            for status, (singular, plural) in copy["totals"].items() if counts[status]
        )
        detail = f'<p class="summary-detail">{escape(breakdown)}</p>' if breakdown else ""
        cards.append(f"""
          <article class="summary-card">
            <p class="runtime-name" title="{escape(version)}">{escape(name)} {escape(build)}</p>
            <p class="score">{passed} / {len(rows)}</p>
            <progress max="{len(rows)}" value="{passed}" aria-label="{escape(label)}"></progress>
            {detail}
          </article>
        """)
    return "".join(cards)


def case_details(row, runtimes, language, copy):
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
        detail = outcome_detail(row["outcomes"][runtime["id"]], language)
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
        cells = [f'<th scope="row">{case_details(row, runtimes, language, copy)}</th>']
        cells.extend(f'<td>{badge(row["outcomes"][runtime["id"]], copy)}</td>' for runtime in runtimes)
        flag = " data-difference" if difference else ""
        table_rows.append(f'<tr data-module="{escape(row["module"])}"{flag}>{"".join(cells)}</tr>')

    modules = sorted({row["module"] for row in rows})
    options = [f'<option value="">{escape(copy["allModules"])}</option>']
    options.extend(f'<option value="{escape(module)}">{escape(module)}</option>' for module in modules)
    return f"""
      <section id="{VIEWS[suite]}" data-dashboard-panel data-comparison>
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
            {table_head(copy["case"], runtimes)}
            <tbody>
              {"".join(table_rows)}
              <tr data-empty hidden><td class="empty" colspan="{len(runtimes) + 1}">{escape(copy["empty"])}</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    """


def render_applications(report, language, copy):
    rows = report.get("applications", [])
    if not rows:
        return f'<p>{escape(copy["appEmpty"])}</p>'
    runtimes = visible_runtimes(rows, report["runtimes"])
    listing = []
    for row in rows:
        name = f'{row["package"]} {row["version"]}'
        description = copy["appNames"][row["id"]]
        cells = [
            f'<th scope="row"><span class="application-name">{escape(name)}</span>{escape(description)}</th>'
        ]
        for runtime in runtimes:
            outcome = row["outcomes"][runtime["id"]]
            detail = outcome_detail(outcome, language)
            label = badge(outcome, copy)
            if detail:
                label = f'<details class="application-detail"><summary>{label}</summary><pre>{escape(detail)}</pre></details>'
            cells.append(f"<td>{label}</td>")
        listing.append("<tr>" + "".join(cells) + "</tr>")
    return f"""
      <div class="table-scroll" role="region" aria-labelledby="application-checks" tabindex="0">
        <table class="application-table">
          {table_head(copy["appCase"], runtimes)}
          <tbody>{"".join(listing)}</tbody>
        </table>
      </div>
    """


def render_use_cases(report, language, copy):
    cards = []
    for case in USE_CASES:
        entry = case[language]
        sources = "".join(
            f'<li><a href="{escape(url)}">{escape(label)}</a></li>'
            for url, label in zip(case["urls"], entry["sources"], strict=True)
        )
        cards.append(f"""
          <article class="use-case">
            <h3>{escape(entry["title"])}</h3>
            <p>{escape(entry["text"])}</p>
            <ul class="sources">{sources}</ul>
          </article>
        """)
    return f"""
      <section id="{VIEWS["uses"]}" data-dashboard-panel>
        <h2>{escape(copy["usesTitle"])}</h2>
        <div class="use-case-grid">{"".join(cards)}</div>
        <h2 id="application-checks">{escape(copy["appTitle"])}</h2>
        <p class="description">{escape(copy["appMethod"])}</p>
        {render_applications(report, language, copy)}
      </section>
    """


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
        useCases=render_use_cases(report, language, copy),
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
