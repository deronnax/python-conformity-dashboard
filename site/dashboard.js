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
  let contractName = parameters.get("contract") ?? "";
  // Most cases pass, so the tables open on differences. ?diff=0 lists every case.
  let differencesOnly = parameters.get("diff") !== "0";
  const tables = [...document.querySelectorAll("[data-comparison]")].map((panel) => ({
    controls: panel.querySelector(".filters"),
    module: panel.querySelector("[data-module-filter]"),
    differences: panel.querySelector("[data-difference-filter]"),
    // Only the shared cases have a contract filter.
    contract: panel.querySelector("[data-contract-filter]"),
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
      let contract = "";
      if (table.contract) {
        table.contract.value = contractName;
        contract = table.contract.value;
      }
      let visible = 0;
      for (const row of table.rows) {
        row.hidden = Boolean((filter && row.dataset.module !== filter)
          || (contract && row.dataset.contract !== contract)
          || (differencesOnly && !row.hasAttribute("data-difference")));
        if (!row.hidden) visible += 1;
      }
      table.empty.hidden = visible !== 0;
      const message = differencesOnly && !filter && !contract ? "differences" : "filtered";
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
    table.contract?.addEventListener("change", () => {
      contractName = table.contract.value;
      filterRows();
    });
    table.differences.addEventListener("change", () => {
      differencesOnly = table.differences.checked;
      filterRows();
    });
  }

  const panels = [...document.querySelectorAll("[data-dashboard-panel]")];
  const navigation = document.querySelectorAll("[data-dashboard-link]");
  // A link to a row shows that row even when the filters hide it, and opens its details.
  function reveal(row) {
    if (row.hidden) {
      moduleName = "";
      contractName = "";
      differencesOnly = false;
      filterRows();
    }
    for (const details of row.querySelectorAll("details")) details.open = true;
    row.scrollIntoView({ block: "center" });
  }

  function selectView() {
    const anchor = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const selected = anchor?.closest("[data-dashboard-panel]") ?? panels[0];
    for (const panel of panels) panel.hidden = panel !== selected;
    for (const link of navigation) {
      if (link.hash === `#${selected.id}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
    if (anchor?.tagName === "TR") reveal(anchor);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Without the asynchronous clipboard (file:// pages), select a temporary copy.
      const area = Object.assign(document.createElement("textarea"), { value: text });
      document.body.append(area);
      area.select();
      const copied = document.execCommand("copy");
      area.remove();
      return copied;
    }
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy]");
    if (!button) return;
    const label = button.textContent;
    if (await copyText(button.dataset.copy)) {
      button.textContent = button.dataset.copied;
      setTimeout(() => { button.textContent = label; }, 1500);
    }
  });

  // Switching language or Python version keeps the view and the filters.
  for (const link of [...languageLinks, ...document.querySelectorAll("[data-version-link]")]) {
    link.addEventListener("click", (event) => {
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const target = new URL(link.href);
      target.hash = location.hash;
      if (moduleName) target.searchParams.set("module", moduleName);
      if (contractName) target.searchParams.set("contract", contractName);
      if (!differencesOnly) target.searchParams.set("diff", "0");
      location.assign(target);
    });
  }
  window.addEventListener("hashchange", selectView);
  filterRows();
  selectView();
}

function initializeCharts() {
  for (const chart of document.querySelectorAll("[data-chart]")) {
    const tooltip = chart.querySelector(".tooltip");
    const crosshair = chart.querySelector(".crosshair");
    const svg = chart.querySelector("svg");

    function hide() {
      tooltip.hidden = true;
      crosshair.hidden = true;
    }

    function show(band) {
      let rows = [];
      try {
        rows = JSON.parse(band.dataset.readout);
      } catch {
        return;
      }
      tooltip.replaceChildren();
      const heading = document.createElement("p");
      heading.textContent = band.dataset.date;
      tooltip.append(heading);
      for (const [name, value, token] of rows) {
        const row = document.createElement("div");
        const key = document.createElement("span");
        key.className = `line-key series-${token}`;
        const label = document.createElement("span");
        label.textContent = name;
        const number = document.createElement("strong");
        number.textContent = value;
        row.append(key, label, number);
        tooltip.append(row);
      }
      crosshair.setAttribute("x1", band.dataset.x);
      crosshair.setAttribute("x2", band.dataset.x);
      crosshair.hidden = false;
      tooltip.hidden = false;
      const frame = chart.getBoundingClientRect();
      const box = band.getBoundingClientRect();
      const centre = box.left + box.width / 2 - frame.left;
      const room = frame.width - tooltip.offsetWidth - 8;
      const side = centre > frame.width / 2 ? centre - tooltip.offsetWidth - 12 : centre + 12;
      tooltip.style.left = `${Math.max(8, Math.min(side, room))}px`;
      tooltip.style.top = `${svg.getBoundingClientRect().top - frame.top + 8}px`;
    }

    for (const band of chart.querySelectorAll("[data-readout]")) {
      band.addEventListener("pointerenter", () => show(band));
      band.addEventListener("focus", () => show(band));
      band.addEventListener("pointerleave", hide);
      band.addEventListener("blur", hide);
    }
  }
}

initializeDashboard();
initializeCharts();
