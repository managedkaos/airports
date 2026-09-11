let allRows = [];
let searchQuery = "";
let sortColumn = "code";
let sortDirection = 1;

// Use text nodes so airport names remain literal text.
function textElement(tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  element.className = className;
  return element;
}

function renderTable() {
  const rows = allRows.filter((airport) =>
    `${airport.code} ${airport.name} ${airport.city} ${airport.country}`.toLowerCase().includes(searchQuery)
  ).sort((a, b) => sortDirection * (a[sortColumn].localeCompare(b[sortColumn]) || a.code.localeCompare(b.code)));
  const body = document.getElementById("airportTableBody");
  body.replaceChildren();
  for (const airport of rows) {
    const row = document.createElement("tr");
    const code = row.insertCell();
    code.append(textElement("span", airport.code, "airport-code-badge"));
    const location = row.insertCell();
    location.append(textElement("strong", `${airport.city}, ${airport.country}`), textElement("small", airport.name));
    row.insertCell().textContent = formatLocalTime(airport);
    row.insertCell().textContent = formatTimeZone(airport);
    row.insertCell().append(textElement("span", formatWeekend(airport), "day-status"));
    body.append(row);
  }
  if (!rows.length) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 5;
    cell.className = "empty-state";
    cell.textContent = "No airports match your search.";
  }
  document.getElementById("airportCount").textContent = `${rows.length} of ${allRows.length} airports`;
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("searchInput").addEventListener("input", (event) => {
    searchQuery = event.target.value.trim().toLowerCase();
    renderTable();
  });
  document.querySelectorAll("button[data-sort]").forEach((button) => {
    button.addEventListener("click", () => {
      sortDirection = sortColumn === button.dataset.sort ? -sortDirection : 1;
      sortColumn = button.dataset.sort;
      document.querySelectorAll("button[data-sort]").forEach((item) => {
        const active = item.dataset.sort === sortColumn;
        item.parentElement.setAttribute("aria-sort", active ? (sortDirection === 1 ? "ascending" : "descending") : "none");
        item.textContent = (item.dataset.sort === "code" ? "Code" : "Location / Airport") + (active ? (sortDirection === 1 ? " ↑" : " ↓") : "");
      });
      renderTable();
    });
  });
  initPolling((data) => { allRows = data.results; renderTable(); });
});
