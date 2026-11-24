const report = JSON.parse(document.querySelector("#results").textContent);
const moduleFilter = document.querySelector("#module");
const onlyDifferences = document.querySelector("#only-differences");
const tableHead = document.querySelector("#table-head");
const tableBody = document.querySelector("#table-body");
const buttons = document.querySelectorAll("[data-suite]");

const statuses = {
  passed: "Réussi",
  different: "Différent",
  missing: "API absente",
  skipped: "Ignoré",
  error: "Erreur du test",
  blocked: "Mesure bloquée",
  crash: "Processus interrompu",
  timeout: "Délai dépassé",
  unverified: "Référence invalide",
};

const descriptions = {
  common: "Les mêmes appels sur chaque interpréteur. Chaque valeur ou exception est comparée à la référence CPython.",
  upstream: "Des méthodes de test sélectionnées dans le code source de CPython, exécutées sur CPython et PyPy.",
};

const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
document.querySelector("#metadata").textContent =
  `Référence CPython ${report.reference} · ${report.platform} · ${date.format(new Date(report.generatedAt))}`;

let suite = "common";

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function runtimesFor(rows) {
  return report.runtimes.filter((runtime) => rows.some((row) => runtime.id in row.outcomes));
}

function renderSummaries(rows, runtimes) {
  const cards = runtimes.map((runtime) => {
    const outcomes = rows.map((row) => row.outcomes[runtime.id]);
    const passed = outcomes.filter((outcome) => outcome.status === "passed").length;
    const card = element("article", undefined, "summary-card");
    const progress = element("progress");
    progress.max = rows.length;
    progress.value = passed;
    progress.setAttribute("aria-label", `Cas réussis sur ${runtime.name}`);
    const version = runtime.version.split("\n");
    let build = version[0].split(" ")[0];
    const namedBuild = version.join(" ").match(/(?:PyPy|MicroPython) v?([\d.]+)/i);
    if (namedBuild && runtime.id !== "cpython") build = namedBuild[1];
    const label = element("p", `${runtime.name} ${build}`, "runtime-name");
    label.title = runtime.version;
    card.append(label, element("p", `${passed} / ${rows.length}`, "score"), progress);
    const remaining = Object.entries(statuses)
      .filter(([status]) => status !== "passed")
      .map(([status, label]) => [outcomes.filter((outcome) => outcome.status === status).length, label])
      .filter(([count]) => count > 0)
      .map(([count, label]) => `${count} ${label.toLowerCase()}`);
    if (remaining.length) card.append(element("p", remaining.join(" · "), "summary-detail"));
    return card;
  });
  document.querySelector("#summaries").replaceChildren(...cards);
}

function caseCell(row, runtimes) {
  const cell = element("th");
  cell.scope = "row";
  const details = element("details");
  const toggle = element("summary");
  if (row.api) {
    toggle.append(element("code", row.api), element("span", row.title, "case-title"));
  } else {
    toggle.append(element("code", row.title), element("span", row.module, "case-title"));
  }
  const content = element("div", undefined, "case-detail");
  if (row.code) content.append(element("pre", row.code));
  const source = element("a", "Voir le test source");
  source.href = row.source;
  source.title = row.sourceTest;
  content.append(source);
  for (const runtime of runtimes) {
    const outcome = row.outcomes[runtime.id];
    if (outcome.detail) {
      content.append(element("p", runtime.name, "detail-runtime"), element("pre", outcome.detail));
    }
  }
  details.append(toggle, content);
  cell.append(details);
  return cell;
}

function renderRows() {
  const rows = report[suite];
  const runtimes = runtimesFor(rows);
  const filter = moduleFilter.value;
  const filtered = rows.filter((row) => !filter || row.module === filter).filter((row) =>
    !onlyDifferences.checked || Object.values(row.outcomes).some((outcome) => outcome.status !== "passed")
  );
  const header = element("tr");
  for (const title of ["Cas", ...runtimes.map((runtime) => runtime.name)]) {
    const cell = element("th", title);
    cell.scope = "col";
    header.append(cell);
  }
  tableHead.replaceChildren(header);
  const listing = filtered.map((row) => {
    const line = element("tr");
    line.append(caseCell(row, runtimes));
    for (const runtime of runtimes) {
      const status = row.outcomes[runtime.id].status;
      const cell = element("td");
      cell.append(element("span", statuses[status], `status ${status}`));
      line.append(cell);
    }
    return line;
  });
  if (!listing.length) {
    const line = element("tr");
    const cell = element("td", "Aucun cas pour ces filtres.", "empty");
    cell.colSpan = runtimes.length + 1;
    line.append(cell);
    listing.push(line);
  }
  tableBody.replaceChildren(...listing);
  document.querySelector("#count").textContent = `${filtered.length} / ${rows.length} cas`;
}

function renderSuite() {
  const rows = report[suite];
  const previousModule = moduleFilter.value;
  const modules = [...new Set(rows.map((row) => row.module))].sort();
  moduleFilter.replaceChildren(new Option("Tous les modules", ""), ...modules.map((module) => new Option(module, module)));
  if (modules.includes(previousModule)) moduleFilter.value = previousModule;
  document.querySelector("#description").textContent = descriptions[suite];
  renderSummaries(rows, runtimesFor(rows));
  renderRows();
}

for (const button of buttons) {
  button.addEventListener("click", () => {
    suite = button.dataset.suite;
    for (const item of buttons) item.setAttribute("aria-pressed", String(item === button));
    renderSuite();
  });
}
moduleFilter.addEventListener("change", renderRows);
onlyDifferences.addEventListener("change", renderRows);
renderSuite();
