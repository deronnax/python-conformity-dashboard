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
    subtitle: "Compare Python implementations by use case, application and standard library behavior.",
    language: "Language",
    download: "Download results (JSON)",
    comparison: "Comparison results",
    suite: "Dashboard view",
    usesTab: "Use cases",
    usesTitle: "Why choose a different Python?",
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
    appTitle: "Application checks",
    appMethod: "The checks exercise these scenarios with pinned packages. NumPy requires a Linux x86-64 wheel that matches the interpreter’s native ABI. These checks record behavior and package availability.",
    appEmpty: "No application checks were run for this report.",
    appCase: "Scenario",
    noWheel: "No matching wheel",
    appNames: {
      "django-template": "Render a template with loops and HTML escaping",
      "django-sqlite": "Query SQLite with the ORM and roll back a transaction",
      "bottle-route": "Dispatch a WSGI route and return JSON",
      "numpy-array": "Broadcast over a strided array and solve a linear system",
    },
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
    subtitle: "Comparer les implémentations Python par usage, application et comportement de la bibliothèque standard.",
    language: "Langue",
    download: "Télécharger les résultats (JSON)",
    comparison: "Résultats de la comparaison",
    suite: "Vue du tableau de bord",
    usesTab: "Cas d’usage",
    usesTitle: "Pourquoi choisir un autre Python ?",
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
    appTitle: "Tests applicatifs",
    appMethod: "Les scénarios utilisent des versions de paquets fixées. NumPy nécessite un paquet binaire Linux x86-64 qui correspond à l’ABI native de l’interpréteur. Ces tests mesurent le comportement et la disponibilité des paquets.",
    appEmpty: "Ce rapport ne contient aucun test applicatif.",
    appCase: "Scénario",
    noWheel: "Aucun binaire compatible",
    appNames: {
      "django-template": "Rendre un gabarit avec des boucles et de l’échappement HTML",
      "django-sqlite": "Interroger SQLite avec l’ORM et annuler une transaction",
      "bottle-route": "Traiter une route WSGI et renvoyer du JSON",
      "numpy-array": "Diffuser une opération sur une vue à pas et résoudre un système linéaire",
    },
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

const useCases = [
  {
    en: {
      title: "Long-running Python code",
      text: "PortaOne reported using PyPy to speed up SIP call processing in 2024. A just-in-time compiler can help a service or worker that runs the same Python code repeatedly, once it has warmed up.",
      sources: ["PortaOne’s deployment report", "PyPy performance guide"],
    },
    fr: {
      title: "Code Python de longue durée",
      text: "PortaOne a décrit en 2024 comment PyPy accélérait le traitement de ses appels SIP. La compilation à la volée peut accélérer un service ou un processus de traitement qui exécute le même code Python de façon répétée, après une phase de chauffe.",
      sources: ["Retour de déploiement de PortaOne", "Guide de performance PyPy"],
    },
    urls: ["https://pypy.org/posts/2024/08/portaone.html", "https://pypy.org/performance.html"],
  },
  {
    en: {
      title: "Web applications and small APIs",
      text: "Lincoln Loop tested PyPy on queries from a Django application. Django documents support for corresponding PyPy versions. Templates, database drivers and deployment dependencies each affect how an app runs. Bottle provides a lightweight WSGI example.",
      sources: ["Lincoln Loop’s Django benchmark", "Django’s PyPy guidance", "Bottle documentation"],
    },
    fr: {
      title: "Applications web et petites API",
      text: "Lincoln Loop a évalué PyPy sur les requêtes d’une application Django. Django documente la compatibilité avec les versions correspondantes de PyPy. Le rendu, les pilotes de base de données et les dépendances de déploiement influencent l’exécution. Bottle fournit un exemple WSGI léger.",
      sources: ["Benchmark Django de Lincoln Loop", "Documentation Django sur PyPy", "Documentation Bottle"],
    },
    urls: ["https://lincolnloop.com/blog/faster-django-sites-pypy/", "https://docs.djangoproject.com/en/5.2/topics/performance/#pypy",
      "https://bottlepy.org/docs/stable/"],
  },
  {
    en: {
      title: "Scientific computing",
      text: "NumPy relies on native extensions. Its PyPI releases list separate wheels for supported interpreter ABIs, and GraalPy publishes compatible builds through its own index. Check the interpreter release and the packages your project needs together.",
      sources: ["NumPy 2.4.4 distributions", "GraalPy package compatibility"],
    },
    fr: {
      title: "Calcul scientifique",
      text: "NumPy repose sur des extensions natives. Ses distributions PyPI proposent des paquets binaires adaptés aux ABI prises en charge, et GraalPy publie des binaires dans son propre index. La compatibilité dépend de la version de l’interpréteur et des paquets utilisés par le projet.",
      sources: ["Distributions NumPy 2.4.4", "Compatibilité des paquets GraalPy"],
    },
    urls: ["https://pypi.org/project/numpy/2.4.4/#files", "https://graalpy.org/python-developers/compatibility/"],
  },
  {
    en: {
      title: "Python inside a JVM application",
      text: "GraalPy can embed Python libraries and scripting in Java, Kotlin or Scala applications. The Quarkiverse integration exposes Python functions as managed Java beans. This scenario uses the JVM embedding API.",
      sources: ["Quarkus GraalPy integration", "GraalPy embedding documentation"],
    },
    fr: {
      title: "Python dans une application JVM",
      text: "GraalPy permet d’intégrer des bibliothèques et des scripts Python dans des applications Java, Kotlin ou Scala. L’intégration Quarkiverse expose des fonctions Python sous forme de beans Java gérés. Cet usage passe par l’API d’intégration JVM.",
      sources: ["Intégration GraalPy pour Quarkus", "Documentation d’intégration GraalPy"],
    },
    urls: ["https://docs.quarkiverse.io/quarkus-graalpy/dev/index.html", "https://graalpy.org/jvm-developers/docs/"],
  },
  {
    en: {
      title: "Python scripting in Rust and WebAssembly",
      text: "Robot Rumble embeds RustPython to run bot code and exchange structured values with its Rust host. RustPython also has an experimental WebAssembly target with a browser demo.",
      sources: ["Robot Rumble’s runner", "RustPython WebAssembly documentation"],
    },
    fr: {
      title: "Scripts Python dans Rust et WebAssembly",
      text: "Robot Rumble embarque RustPython pour exécuter les scripts des robots et échanger des valeurs structurées avec son application Rust. RustPython propose aussi une cible WebAssembly expérimentale avec une démo dans le navigateur.",
      sources: ["Exécuteur de Robot Rumble", "Documentation WebAssembly de RustPython"],
    },
    urls: ["https://github.com/robot-rumble/logic/blob/master/lang-runners/python/src/main.rs",
      "https://github.com/RustPython/RustPython/blob/main/wasm/README.md"],
  },
  {
    en: {
      title: "Programming contests",
      text: "AtCoder offers PyPy alongside CPython for time-limited submissions. Its published environment uses PyPy 7.3.20 and includes NumPy 2.3.2, an example of a package set selected for a specific runtime release.",
      sources: ["AtCoder’s supported languages and libraries"],
    },
    fr: {
      title: "Concours de programmation",
      text: "AtCoder propose PyPy aux côtés de CPython pour les soumissions à temps limité. Son environnement publié associe PyPy 7.3.20 à NumPy 2.3.2, un exemple de paquets choisis pour une version précise de l’interpréteur.",
      sources: ["Langages et bibliothèques pris en charge par AtCoder"],
    },
    urls: ["https://img.atcoder.jp/file/language-update/2025-10/language-list.html"],
  },
];

const preferenceKey = "python-conformity-language";

let suite = "uses";
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

function tableHeader(titles) {
  const header = element("tr");
  for (const title of titles) {
    const cell = element("th", title);
    cell.scope = "col";
    header.append(cell);
  }
  return header;
}

function renderUseCases() {
  const cards = useCases.map((entry) => {
    const description = entry[language];
    const card = element("article", undefined, "use-case");
    const sources = element("ul", undefined, "sources");
    entry.urls.forEach((url, index) => {
      const item = element("li");
      const link = element("a", description.sources[index]);
      link.href = url;
      item.append(link);
      sources.append(item);
    });
    card.append(element("h3", description.title), element("p", description.text), sources);
    return card;
  });
  document.querySelector("#use-case-list").replaceChildren(...cards);
  const rows = report.applications ?? [];
  document.querySelector("#application-table").hidden = !rows.length;
  document.querySelector("#application-empty").hidden = Boolean(rows.length);
  if (!rows.length) return;

  const runtimes = runtimesFor(rows);
  document.querySelector("#application-head").replaceChildren(tableHeader([copy.appCase, ...runtimes.map((runtime) => runtime.name)]));
  const listing = rows.map((row) => {
    const line = element("tr");
    const label = element("th");
    label.scope = "row";
    label.append(element("span", `${row.package} ${row.version}`, "application-name"),
      element("span", copy.appNames[row.id]));
    line.append(label);
    for (const runtime of runtimes) {
      const cell = element("td");
      const outcome = row.outcomes[runtime.id];
      const text = outcome.status === "noWheel" ? copy.noWheel : copy.statuses[outcome.status];
      const badge = element("span", text, `status ${outcome.status}`);
      if (outcome.detail) {
        const details = element("details", undefined, "application-detail");
        const summary = element("summary");
        summary.append(badge);
        details.append(summary, element("pre", outcome.detail));
        cell.append(details);
      } else {
        cell.append(badge);
      }
      line.append(cell);
    }
    return line;
  });
  document.querySelector("#application-body").replaceChildren(...listing);
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
  tableHead.replaceChildren(tableHeader([copy.case, ...runtimes.map((runtime) => runtime.name)]));
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
  const showingUses = suite === "uses";
  document.querySelector("#use-cases").hidden = !showingUses;
  document.querySelector("#api-comparison").hidden = showingUses;
  if (showingUses) {
    renderUseCases();
    return;
  }
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
