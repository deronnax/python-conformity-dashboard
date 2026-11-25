const report = JSON.parse(document.querySelector("#results").textContent);
const languageSelect = document.querySelector("#language");
const moduleFilter = document.querySelector("#module");
const onlyDifferences = document.querySelector("#only-differences");
const tableHead = document.querySelector("#table-head");
const tableBody = document.querySelector("#table-body");
const buttons = document.querySelectorAll("[data-suite]");

const translations = {
  en: {
    title: "Python Conformity",
    subtitle: "Observed behavior of public standard library APIs.",
    language: "Language",
    download: "Download results (JSON)",
    comparison: "Comparison results",
    suite: "Test suite",
    commonTab: "Shared cases",
    upstreamTab: "CPython tests",
    summaries: "Results by interpreter",
    module: "Module",
    onlyDifferences: "Differences and unmeasured cases",
    caseTable: "Test case table",
    methodology: "Methodology and scope",
    methodCases: "Shared cases compare observed types and values with CPython. For invalid inputs, they check whether callers can catch the exception using the expected public class.",
    methodUpstream: "The CPython tests view runs selected upstream test methods on CPython and PyPy. The JSON test harness enables the CPython accelerator when available. Shared cases import the module as usual.",
    methodScope: "These results apply to the cases, versions and platform shown. The shared cases cover APIs available in CPython 3.11. A module can be unavailable in a specific build. Each row links to the source test.",
    reference: "CPython reference",
    source: "View source test",
    passedOn: (runtime) => `Cases passed on ${runtime}`,
    case: "Case",
    counts: (shown, total) => `${shown} / ${total} cases`,
    empty: "No cases match these filters.",
    allModules: "All modules",
    descriptions: {
      common: "Each interpreter runs the same calls. Values and exceptions are compared with the CPython reference.",
      upstream: "Selected test methods from the CPython source tree, run on CPython and PyPy.",
    },
    statuses: {
      passed: "Passed", different: "Different", missing: "Missing API", skipped: "Skipped",
      error: "Test error", blocked: "Measurement blocked", crash: "Process interrupted",
      timeout: "Timed out", unverified: "Invalid reference",
    },
    totals: {
      different: ["difference", "differences"], missing: ["missing API", "missing APIs"],
      skipped: ["skipped test", "skipped tests"], error: ["test error", "test errors"],
      blocked: ["blocked measurement", "blocked measurements"], crash: ["interrupted process", "interrupted processes"],
      timeout: ["timeout", "timeouts"], unverified: ["invalid reference", "invalid references"],
    },
  },
  fr: {
    title: "Conformité Python",
    subtitle: "Comportements observés sur les API publiques de la bibliothèque standard.",
    language: "Langue",
    download: "Télécharger les résultats (JSON)",
    comparison: "Résultats de la comparaison",
    suite: "Corpus",
    commonTab: "Cas communs",
    upstreamTab: "Tests CPython",
    summaries: "Résultats par interpréteur",
    module: "Module",
    onlyDifferences: "Écarts et cas non mesurés",
    caseTable: "Tableau des cas",
    methodology: "Méthode et périmètre",
    methodCases: "Les cas communs comparent les types et valeurs observés à ceux de CPython. Pour les entrées invalides, on vérifie que le code appelant peut intercepter l’exception avec la classe publique attendue.",
    methodUpstream: "La vue Tests CPython exécute une sélection de méthodes d’origine sur CPython et PyPy. Pour JSON, le harnais active son accélérateur CPython uniquement s’il est disponible. Les cas communs chargent le module normalement.",
    methodScope: "Les résultats portent sur ces cas, ces versions et cette plateforme. Les cas communs couvrent des API disponibles dans CPython 3.11. Un module peut être absent d’un binaire donné. Chaque ligne donne accès à son cas source.",
    reference: "Référence CPython",
    source: "Voir le test source",
    passedOn: (runtime) => `Cas réussis sur ${runtime}`,
    case: "Cas",
    counts: (shown, total) => `${shown} / ${total} cas`,
    empty: "Aucun cas pour ces filtres.",
    allModules: "Tous les modules",
    descriptions: {
      common: "Les mêmes appels sur chaque interpréteur. Chaque valeur ou exception est comparée à la référence CPython.",
      upstream: "Des méthodes de test sélectionnées dans le code source de CPython, exécutées sur CPython et PyPy.",
    },
    statuses: {
      passed: "Réussi", different: "Différent", missing: "API absente", skipped: "Ignoré",
      error: "Erreur du test", blocked: "Mesure bloquée", crash: "Processus interrompu",
      timeout: "Délai dépassé", unverified: "Référence invalide",
    },
    totals: {
      different: ["écart", "écarts"], missing: ["API absente", "API absentes"],
      skipped: ["test ignoré", "tests ignorés"], error: ["erreur de test", "erreurs de test"],
      blocked: ["mesure bloquée", "mesures bloquées"], crash: ["processus interrompu", "processus interrompus"],
      timeout: ["délai dépassé", "délais dépassés"], unverified: ["référence invalide", "références invalides"],
    },
  },
};

const preferenceKey = "python-conformity-language";

let suite = "common";
let language = initialLanguage();
let copy = translations[language];

function initialLanguage() {
  try {
    const saved = localStorage.getItem(preferenceKey);
    if (saved === "en" || saved === "fr") return saved;
  } catch {
    // Storage may be disabled, including when opened from disk.
  }
  const preferences = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const locale of preferences) {
    const primary = locale?.split("-")[0].toLowerCase();
    if (primary === "en" || primary === "fr") return primary;
  }
  return "en";
}

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
    progress.setAttribute("aria-label", copy.passedOn(runtime.name));
    const version = runtime.version.split("\n");
    let build = version[0].split(" ")[0];
    const namedBuild = version.join(" ").match(/(?:PyPy|RustPython) v?([\d.]+)/i);
    if (namedBuild && runtime.id !== "cpython") build = namedBuild[1];
    const label = element("p", `${runtime.name} ${build}`, "runtime-name");
    label.title = runtime.version;
    card.append(label, element("p", `${passed} / ${rows.length}`, "score"), progress);
    const remaining = Object.entries(copy.totals)
      .map(([status, labels]) => [outcomes.filter((outcome) => outcome.status === status).length, labels])
      .filter(([count]) => count > 0)
      .map(([count, labels]) => `${count} ${labels[count === 1 ? 0 : 1]}`);
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
    const title = language === "fr" ? (row.titleFr ?? row.title) : row.title;
    toggle.append(element("code", row.api), element("span", title, "case-title"));
  } else {
    toggle.append(element("code", row.title), element("span", row.module, "case-title"));
  }
  const content = element("div", undefined, "case-detail");
  if (row.code) content.append(element("pre", row.code));
  const source = element("a", copy.source);
  source.href = row.source;
  source.title = row.sourceTest;
  content.append(source);
  for (const runtime of runtimes) {
    const outcome = row.outcomes[runtime.id];
    const detail = language === "fr" ? (outcome.detailFr ?? outcome.detail) : outcome.detail;
    if (detail) {
      content.append(element("p", runtime.name, "detail-runtime"), element("pre", detail));
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
  for (const title of [copy.case, ...runtimes.map((runtime) => runtime.name)]) {
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
      cell.append(element("span", copy.statuses[status], `status ${status}`));
      line.append(cell);
    }
    return line;
  });
  if (!listing.length) {
    const line = element("tr");
    const cell = element("td", copy.empty, "empty");
    cell.colSpan = runtimes.length + 1;
    line.append(cell);
    listing.push(line);
  }
  tableBody.replaceChildren(...listing);
  document.querySelector("#count").textContent = copy.counts(filtered.length, rows.length);
}

function renderSuite() {
  const rows = report[suite];
  const previousModule = moduleFilter.value;
  const modules = [...new Set(rows.map((row) => row.module))].sort();
  moduleFilter.replaceChildren(new Option(copy.allModules, ""), ...modules.map((module) => new Option(module, module)));
  if (modules.includes(previousModule)) moduleFilter.value = previousModule;
  document.querySelector("#description").textContent = copy.descriptions[suite];
  renderSummaries(rows, runtimesFor(rows));
  renderRows();
}

function renderLanguage() {
  document.documentElement.lang = language;
  document.title = copy.title;
  languageSelect.value = language;
  for (const node of document.querySelectorAll("[data-message]")) {
    node.textContent = copy[node.dataset.message];
  }
  for (const node of document.querySelectorAll("[data-label]")) {
    node.setAttribute("aria-label", copy[node.dataset.label]);
  }
  const date = new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" });
  document.querySelector("#metadata").textContent =
    `${copy.reference} ${report.reference} · ${report.platform} · ${date.format(new Date(report.generatedAt))}`;
  renderSuite();
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
languageSelect.addEventListener("change", () => {
  language = languageSelect.value;
  copy = translations[language];
  try {
    localStorage.setItem(preferenceKey, language);
  } catch {
    // The selection still applies to the current page.
  }
  renderLanguage();
});
renderLanguage();
