const preferenceKey = "python-conformity-language";
const supportedLanguages = ["en", "fr"];

function preferredLanguage(pageLanguage, explicit) {
  if (supportedLanguages.includes(explicit)) return explicit;
  if (pageLanguage === "fr") return pageLanguage;
  try {
    const saved = localStorage.getItem(preferenceKey);
    if (supportedLanguages.includes(saved)) return saved;
  } catch {
    // Storage can be unavailable when viewing the archive directly.
  }
  const locales = navigator.languages?.length ? navigator.languages : [navigator.language];
  const available = locales.map((locale) => locale?.split("-")[0].toLowerCase());
  return available.find((locale) => supportedLanguages.includes(locale)) ?? "en";
}

function initializeDashboard() {
  const pageLanguage = document.documentElement.lang;
  const parameters = new URLSearchParams(location.search);
  const explicit = parameters.get("lang");
  const language = preferredLanguage(pageLanguage, explicit);
  const languageLinks = [...document.querySelectorAll("[data-language-link]")];
  if (language !== pageLanguage) {
    const target = new URL(languageLinks.find((link) => link.hreflang === language).href);
    target.search = location.search;
    target.hash = location.hash;
    location.replace(target);
    return;
  }
  if (explicit === pageLanguage) {
    try {
      localStorage.setItem(preferenceKey, pageLanguage);
    } catch {
      // The language remains explicit in the URL.
    }
  }

  const stamp = document.querySelector("time[datetime]");
  const date = new Intl.DateTimeFormat(pageLanguage, { dateStyle: "medium", timeStyle: "short" });
  stamp.textContent = date.format(new Date(stamp.dateTime));

  let moduleName = parameters.get("module") ?? "";
  // Most cases pass, so the tables open on differences. ?diff=0 lists every case.
  let differencesOnly = parameters.get("diff") !== "0";
  const tables = [...document.querySelectorAll("[data-comparison]")].map((panel) => ({
    controls: panel.querySelector(".filters"),
    module: panel.querySelector("[data-module-filter]"),
    differences: panel.querySelector("[data-difference-filter]"),
    count: panel.querySelector("[data-case-count]"),
    rows: [...panel.querySelectorAll("[data-module]")],
    empty: panel.querySelector("[data-empty]"),
    emptyMessage: panel.querySelector("[data-empty] td"),
  }));

  function filterRows() {
    for (const table of tables) {
      table.module.value = moduleName;
      const filter = table.module.value;
      table.differences.checked = differencesOnly;
      let visible = 0;
      for (const row of table.rows) {
        row.hidden = Boolean((filter && row.dataset.module !== filter) || (differencesOnly && !row.hasAttribute("data-difference")));
        if (!row.hidden) visible += 1;
      }
      table.empty.hidden = visible !== 0;
      const message = differencesOnly && !filter ? "differences" : "filtered";
      table.emptyMessage.textContent = table.emptyMessage.dataset[message];
      table.count.textContent = `${visible} / ${table.rows.length} ${table.count.dataset.unit}`;
    }
  }

  for (const table of tables) {
    table.controls.hidden = false;
    table.module.addEventListener("change", () => {
      moduleName = table.module.value;
      filterRows();
    });
    table.differences.addEventListener("change", () => {
      differencesOnly = table.differences.checked;
      filterRows();
    });
  }

  const panels = [...document.querySelectorAll("[data-dashboard-panel]")];
  const navigation = document.querySelectorAll("[data-dashboard-link]");
  function selectView() {
    const anchor = document.getElementById(location.hash.slice(1));
    const selected = anchor?.closest("[data-dashboard-panel]") ?? panels[0];
    for (const panel of panels) panel.hidden = panel !== selected;
    for (const link of navigation) {
      if (link.hash === `#${selected.id}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }

  for (const link of languageLinks) {
    link.addEventListener("click", (event) => {
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const target = new URL(link.href);
      target.hash = location.hash;
      if (moduleName) target.searchParams.set("module", moduleName);
      if (!differencesOnly) target.searchParams.set("diff", "0");
      location.assign(target);
    });
  }
  window.addEventListener("hashchange", selectView);
  selectView();
  filterRows();
}

initializeDashboard();
