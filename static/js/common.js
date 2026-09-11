/** Shared airport presentation and minute-level refresh. */
let currentData = null;
let isRefreshing = false;
let dataCallback = null;

// Display the server's local wall time directly, preserving its date and DST offset.
function formatLocalTime(airport) {
  return airport.local_time.slice(0, 16).replace("T", " ");
}

function formatTimeZone(airport) {
  const offset = airport.local_time.match(/([+-]\d{2}:\d{2}|Z)$/)[1];
  return `${airport.timezone} (UTC${offset === "Z" ? "+00:00" : offset})`;
}

function formatWeekend(airport) {
  return airport.is_weekend ? "Weekend" : "Weekday";
}

function formatUpdated(timestamp) {
  return new Date(timestamp).toISOString().slice(0, 19).replace("T", " ") + " UTC";
}

async function fetchAirports() {
  if (isRefreshing) return;
  isRefreshing = true;
  const button = document.getElementById("refreshBtn");
  button.disabled = true;
  try {
    const response = await fetch("/api/airports", { cache: "no-store", signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    dataCallback(data);
    currentData = data;
    document.getElementById("updatedText").textContent = `Updated ${formatUpdated(data.generated_at)}`;
    document.getElementById("errorBanner").hidden = true;
  } catch (error) {
    const retained = currentData ? ` Showing values last updated ${formatUpdated(currentData.generated_at)}.` : "";
    document.getElementById("errorMessage").textContent = `Unable to load airport times.${retained} Retry the connection.`;
    document.getElementById("errorBanner").hidden = false;
    document.getElementById("updatedText").textContent = currentData ? `Last updated ${formatUpdated(currentData.generated_at)}` : "Airport times unavailable";
    if (!currentData && document.getElementById("airportTableBody")) {
      document.getElementById("airportTableBody").textContent = "";
    }
    console.error("Unable to load airports:", error);
  } finally {
    isRefreshing = false;
    button.disabled = false;
  }
}

function initPolling(callback) {
  dataCallback = callback;
  fetchAirports();
  setInterval(fetchAirports, 60000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) fetchAirports();
  });
  document.getElementById("refreshBtn").addEventListener("click", fetchAirports);
  document.getElementById("errorRetryBtn").addEventListener("click", fetchAirports);
}
