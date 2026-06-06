"use strict";

const STORAGE_KEY = "hdfs-anomaly-dashboard-v1";
const MAX_FILE_BYTES = 4 * 1024 * 1024;
const PAGE_SIZE = 50;

const state = {
  selectedFile: null,
  results: [],
  resultVisible: PAGE_SIZE,
  alertVisible: PAGE_SIZE,
  history: loadHistory(),
};

const pageTitles = {
  dashboard: "Dashboard",
  analyze: "Upload & Analyse",
  alerts: "Alerts Log",
  model: "Model Info",
};

const el = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindUpload();
  bindResults();
  bindAlerts();
  renderAll();
  checkApiStatus();
  const requestedView = new URLSearchParams(window.location.search).get("view");
  if (pageTitles[requestedView]) switchView(requestedView);
  el("currentDate").textContent = new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date());
  if (window.lucide) window.lucide.createIcons();
});

function loadHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return {
      runs: Array.isArray(parsed?.runs) ? parsed.runs : [],
      alerts: Array.isArray(parsed?.alerts) ? parsed.alerts : [],
    };
  } catch {
    return { runs: [], alerts: [] };
  }
}

function saveHistory() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        runs: state.history.runs.slice(0, 100),
        alerts: state.history.alerts.slice(0, 5000),
      }),
    );
  } catch {
    showToast("Browser storage is full. Older alerts were not retained.", true);
  }
}

function bindNavigation() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.viewTarget));
  });
  el("mobileMenu").addEventListener("click", toggleSidebar);
  el("sidebarBackdrop").addEventListener("click", closeSidebar);
}

function switchView(viewName) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  el(`view-${viewName}`).classList.add("active");
  document.querySelector(`[data-view="${viewName}"]`).classList.add("active");
  el("pageTitle").textContent = pageTitles[viewName];
  closeSidebar();
  if (viewName === "dashboard") renderDashboard();
  if (viewName === "alerts") renderAlerts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function toggleSidebar() {
  el("sidebar").classList.toggle("open");
  el("sidebarBackdrop").classList.toggle("visible");
}

function closeSidebar() {
  el("sidebar").classList.remove("open");
  el("sidebarBackdrop").classList.remove("visible");
}

async function checkApiStatus() {
  const container = document.querySelector(".system-state");
  try {
    const response = await fetch("/api/analyze", { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok || payload.status !== "ready") throw new Error(payload.error || "API unavailable");
    el("statusDot").className = "status-dot online";
    el("statusLabel").textContent = "Model online";
    el("statusDetail").textContent = `${payload.model.trees} trees · ${payload.model.features} features`;
    container.classList.remove("offline");
    el("topStatusDot").className = "status-dot small online";
    el("topStatusLabel").textContent = "Random Forest online";
    el("runtimePill").classList.remove("offline");
  } catch {
    el("statusDot").className = "status-dot offline";
    el("statusLabel").textContent = "Runtime unavailable";
    el("statusDetail").textContent = "Retry after deployment";
    container.classList.add("offline");
    el("topStatusDot").className = "status-dot small offline";
    el("topStatusLabel").textContent = "Runtime unavailable";
    el("runtimePill").classList.add("offline");
  }
}

function bindUpload() {
  const dropZone = el("dropZone");
  const fileInput = el("fileInput");

  el("browseButton").addEventListener("click", (event) => {
    event.stopPropagation();
    fileInput.click();
  });
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => setSelectedFile(fileInput.files[0]));
  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("dragging");
    });
  });
  dropZone.addEventListener("drop", (event) => setSelectedFile(event.dataTransfer.files[0]));
  el("removeFile").addEventListener("click", clearSelectedFile);
  el("analyzeButton").addEventListener("click", runAnalysis);
  el("sampleButton").addEventListener("click", loadSample);
}

function setSelectedFile(file) {
  hideAnalysisError();
  if (!file) return;
  if (!/\.(csv|log)$/i.test(file.name)) {
    showAnalysisError("Select a CSV or LOG file.");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    showAnalysisError("The selected file exceeds the 4 MB upload limit.");
    return;
  }
  if (file.size === 0) {
    showAnalysisError("The selected file is empty.");
    return;
  }
  state.selectedFile = file;
  el("selectedFileName").textContent = file.name;
  el("selectedFileMeta").textContent = `${formatBytes(file.size)} · ready for analysis`;
  el("selectedFile").classList.remove("hidden");
  el("analyzeButton").disabled = false;
  el("resultsSection").classList.add("hidden");
}

function clearSelectedFile(event) {
  if (event) event.stopPropagation();
  state.selectedFile = null;
  el("fileInput").value = "";
  el("selectedFile").classList.add("hidden");
  el("analyzeButton").disabled = true;
}

async function loadSample() {
  const button = el("sampleButton");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span>Loading sample';
  try {
    const response = await fetch("/HDFS_demo_feature_matrix.csv");
    if (!response.ok) throw new Error("The bundled sample could not be loaded.");
    const blob = await response.blob();
    const file = new File([blob], "HDFS_demo_feature_matrix.csv", { type: "text/csv" });
    setSelectedFile(file);
    showToast("Sample log ready for analysis.");
  } catch (error) {
    showAnalysisError(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = '<i data-lucide="flask-conical"></i>Use included sample';
    if (window.lucide) window.lucide.createIcons();
  }
}

async function runAnalysis() {
  if (!state.selectedFile) return;

  const button = el("analyzeButton");
  const processing = el("processingPanel");
  const progress = el("progressBar");
  hideAnalysisError();
  el("resultsSection").classList.add("hidden");
  processing.classList.remove("hidden");
  button.disabled = true;
  progress.style.width = "12%";
  el("processingText").textContent = "Uploading the structured log...";

  const progressTimer = window.setInterval(() => {
    const current = Number.parseInt(progress.style.width, 10) || 12;
    progress.style.width = `${Math.min(current + 8, 88)}%`;
    if (current > 38) el("processingText").textContent = "Extracting session event vectors...";
    if (current > 66) el("processingText").textContent = "Running Random Forest inference...";
  }, 650);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "X-File-Name": encodeURIComponent(state.selectedFile.name),
      },
      body: state.selectedFile,
    });
    const payload = await response.json().catch(() => ({ error: "The server returned an invalid response." }));
    if (!response.ok) throw new Error(payload.error || `Analysis failed with status ${response.status}.`);

    progress.style.width = "100%";
    el("processingText").textContent = "Analysis complete.";
    state.results = payload.results;
    state.resultVisible = PAGE_SIZE;
    storeAnalysis(payload);
    renderResults(payload);
    renderAll();
    window.setTimeout(() => {
      processing.classList.add("hidden");
      el("resultsSection").scrollIntoView({ behavior: "smooth", block: "start" });
    }, 350);
    showToast(`${payload.summary.anomalies} anomalies detected in ${payload.file}.`);
  } catch (error) {
    processing.classList.add("hidden");
    showAnalysisError(error.message);
  } finally {
    window.clearInterval(progressTimer);
    button.disabled = false;
  }
}

function storeAnalysis(payload) {
  const run = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    file: payload.file,
    timestamp: new Date().toISOString(),
    total: payload.summary.total,
    normal: payload.summary.normal,
    anomalies: payload.summary.anomalies,
    anomalyRate: payload.summary.anomaly_rate,
  };
  const alerts = payload.results
    .filter((row) => row.Prediction === "Anomaly")
    .map((row) => ({
      id: `${run.id}-${row.BlockId}`,
      blockId: row.BlockId,
      severity: row.Severity,
      confidence: Number(row.Confidence),
      timestamp: row.Timestamp || run.timestamp,
      sourceFile: payload.file,
    }));

  state.history.runs.unshift(run);
  state.history.alerts.unshift(...alerts);
  state.history.runs = state.history.runs.slice(0, 100);
  state.history.alerts = state.history.alerts.slice(0, 5000);
  saveHistory();
}

function renderAll() {
  renderDashboard();
  renderAlerts();
  el("navAlertCount").textContent = compactNumber(state.history.alerts.length);
}

function renderDashboard() {
  const alerts = state.history.alerts;
  const runs = state.history.runs;
  const severity = countSeverity(alerts);
  const latest = alerts[0]?.timestamp;

  el("metricAlerts").textContent = number(alerts.length);
  el("metricCritical").textContent = number(severity.CRITICAL);
  el("metricFiles").textContent = number(runs.length);
  el("metricLatest").textContent = latest ? formatDate(latest, true) : "None";
  el("severityTotal").textContent = `${number(alerts.length)} alerts`;
  el("donutValue").textContent = compactNumber(alerts.length);

  const total = Math.max(alerts.length, 1);
  const colors = {
    CRITICAL: "var(--red)",
    HIGH: "var(--orange)",
    MEDIUM: "var(--amber)",
    LOW: "var(--cyan)",
  };
  let angle = 0;
  const segments = [];
  ["CRITICAL", "HIGH", "MEDIUM", "LOW"].forEach((level) => {
    const next = angle + (severity[level] / total) * 100;
    if (severity[level] > 0) segments.push(`${colors[level]} ${angle}% ${next}%`);
    angle = next;
    el(`severity${titleCase(level)}`).textContent = number(severity[level]);
    el(`bar${titleCase(level)}`).style.width = `${(severity[level] / total) * 100}%`;
  });
  el("severityDonut").style.background = segments.length
    ? `conic-gradient(${segments.join(",")})`
    : "var(--line)";

  const recentBody = el("recentAlertsBody");
  recentBody.innerHTML = alerts.slice(0, 5).map((alert) => `
    <tr>
      <td class="block-id" title="${escapeHtml(alert.blockId)}">${escapeHtml(shortBlock(alert.blockId))}</td>
      <td>${severityBadge(alert.severity)}</td>
      <td>${formatScore(alert.confidence)}</td>
      <td>${formatDate(alert.timestamp, true)}</td>
    </tr>
  `).join("");
  el("recentEmpty").classList.toggle("hidden", alerts.length > 0);
  recentBody.closest("table").classList.toggle("hidden", alerts.length === 0);

  const runList = el("runList");
  runList.innerHTML = runs.slice(0, 5).map((run) => `
    <div class="run-item">
      <div class="run-file"><i data-lucide="file-check-2"></i><div><strong title="${escapeHtml(run.file)}">${escapeHtml(run.file)}</strong><span>${formatDate(run.timestamp)}</span></div></div>
      <div class="run-stat"><strong>${number(run.total)}</strong><span>sessions</span></div>
      <div class="run-stat"><strong>${number(run.anomalies)}</strong><span>anomalies</span></div>
      <div class="run-stat"><strong>${Number(run.anomalyRate).toFixed(2)}%</strong><span>rate</span></div>
    </div>
  `).join("");
  el("runsEmpty").classList.toggle("hidden", runs.length > 0);
  if (window.lucide) window.lucide.createIcons();
}

function bindResults() {
  el("resultSearch").addEventListener("input", () => {
    state.resultVisible = PAGE_SIZE;
    renderResultsTable();
  });
  el("resultFilter").addEventListener("change", () => {
    state.resultVisible = PAGE_SIZE;
    renderResultsTable();
  });
  el("showMoreResults").addEventListener("click", () => {
    state.resultVisible += PAGE_SIZE;
    renderResultsTable();
  });
  el("downloadResults").addEventListener("click", () => {
    const rows = state.results.map((row) => ({
      BlockId: row.BlockId,
      Prediction: row.Prediction,
      Confidence: row.Confidence,
      Severity: row.Severity || "",
      Timestamp: row.Timestamp,
      Source_File: row.Source_File,
    }));
    downloadCsv(rows, `results_${safeDownloadName(state.selectedFile?.name || "hdfs_log")}`);
  });
}

function renderResults(payload) {
  el("resultFileName").textContent = payload.file;
  el("resultTotal").textContent = number(payload.summary.total);
  el("resultNormal").textContent = number(payload.summary.normal);
  el("resultAnomalies").textContent = number(payload.summary.anomalies);
  el("resultRate").textContent = `${Number(payload.summary.anomaly_rate).toFixed(2)}%`;
  el("resultSearch").value = "";
  el("resultFilter").value = "all";
  el("resultsSection").classList.remove("hidden");
  renderResultsTable();
}

function filteredResults() {
  const search = el("resultSearch").value.trim().toLowerCase();
  const filter = el("resultFilter").value;
  return state.results.filter((row) => {
    const matchesSearch = !search || String(row.BlockId).toLowerCase().includes(search);
    const matchesFilter = filter === "all" || row.Prediction === filter;
    return matchesSearch && matchesFilter;
  });
}

function renderResultsTable() {
  const filtered = filteredResults();
  const visible = filtered.slice(0, state.resultVisible);
  el("resultsBody").innerHTML = visible.map((row) => `
    <tr>
      <td class="block-id" title="${escapeHtml(row.BlockId)}">${escapeHtml(row.BlockId)}</td>
      <td><span class="prediction ${row.Prediction.toLowerCase()}">${row.Prediction}</span></td>
      <td>${formatScore(row.Confidence)}</td>
      <td>${row.Severity ? severityBadge(row.Severity) : '<span class="muted">-</span>'}</td>
      <td>${formatDate(row.Timestamp)}</td>
    </tr>
  `).join("");
  el("resultsEmpty").classList.toggle("hidden", filtered.length > 0);
  el("resultsBody").closest("table").classList.toggle("hidden", filtered.length === 0);
  el("resultCount").textContent = filtered.length
    ? `Showing ${number(Math.min(visible.length, filtered.length))} of ${number(filtered.length)} sessions`
    : "No matching sessions";
  el("showMoreResults").classList.toggle("hidden", visible.length >= filtered.length);
}

function bindAlerts() {
  ["alertSearch", "severityFilter", "fileFilter"].forEach((id) => {
    el(id).addEventListener(id === "alertSearch" ? "input" : "change", () => {
      state.alertVisible = PAGE_SIZE;
      renderAlerts();
    });
  });
  el("showMoreAlerts").addEventListener("click", () => {
    state.alertVisible += PAGE_SIZE;
    renderAlerts();
  });
  el("downloadAlerts").addEventListener("click", () => {
    const rows = filteredAlerts().map((alert) => ({
      BlockId: alert.blockId,
      Prediction: "Anomaly",
      Confidence: alert.confidence,
      Severity: alert.severity,
      Timestamp: alert.timestamp,
      Source_File: alert.sourceFile,
    }));
    if (!rows.length) return showToast("There are no alerts to export.", true);
    downloadCsv(rows, "hdfs_alerts_log.csv");
  });
  el("clearHistory").addEventListener("click", () => {
    if (!state.history.alerts.length && !state.history.runs.length) return;
    if (!window.confirm("Clear all analysis and alert history stored in this browser?")) return;
    state.history = { runs: [], alerts: [] };
    localStorage.removeItem(STORAGE_KEY);
    renderAll();
    showToast("Local dashboard history cleared.");
  });
}

function filteredAlerts() {
  const search = el("alertSearch").value.trim().toLowerCase();
  const severity = el("severityFilter").value;
  const file = el("fileFilter").value;
  return state.history.alerts.filter((alert) => {
    const matchesSearch = !search
      || alert.blockId.toLowerCase().includes(search)
      || alert.sourceFile.toLowerCase().includes(search);
    return matchesSearch
      && (severity === "all" || alert.severity === severity)
      && (file === "all" || alert.sourceFile === file);
  });
}

function renderAlerts() {
  const fileSelect = el("fileFilter");
  const selectedFile = fileSelect.value || "all";
  const files = [...new Set(state.history.alerts.map((alert) => alert.sourceFile))].sort();
  fileSelect.innerHTML = '<option value="all">All files</option>'
    + files.map((file) => `<option value="${escapeHtml(file)}">${escapeHtml(file)}</option>`).join("");
  fileSelect.value = files.includes(selectedFile) ? selectedFile : "all";

  const filtered = filteredAlerts();
  const visible = filtered.slice(0, state.alertVisible);
  const severity = countSeverity(filtered);
  el("alertSummary").innerHTML = `
    <span>Showing<strong>${number(filtered.length)}</strong></span>
    <span>Critical<strong>${number(severity.CRITICAL)}</strong></span>
    <span>High<strong>${number(severity.HIGH)}</strong></span>
    <span>Medium<strong>${number(severity.MEDIUM)}</strong></span>
    <span>Low<strong>${number(severity.LOW)}</strong></span>
  `;
  el("alertsBody").innerHTML = visible.map((alert) => `
    <tr>
      <td class="block-id" title="${escapeHtml(alert.blockId)}">${escapeHtml(alert.blockId)}</td>
      <td>${severityBadge(alert.severity)}</td>
      <td>${formatScore(alert.confidence)}</td>
      <td>${escapeHtml(alert.sourceFile)}</td>
      <td>${formatDate(alert.timestamp)}</td>
    </tr>
  `).join("");
  el("alertsEmpty").classList.toggle("hidden", filtered.length > 0);
  el("alertsBody").closest("table").classList.toggle("hidden", filtered.length === 0);
  el("alertCount").textContent = filtered.length
    ? `Showing ${number(Math.min(visible.length, filtered.length))} of ${number(filtered.length)} alerts`
    : "No matching alerts";
  el("showMoreAlerts").classList.toggle("hidden", visible.length >= filtered.length);
}

function showAnalysisError(message) {
  el("analysisErrorText").textContent = message;
  el("analysisError").classList.remove("hidden");
}

function hideAnalysisError() {
  el("analysisError").classList.add("hidden");
}

let toastTimer;
function showToast(message, isError = false) {
  window.clearTimeout(toastTimer);
  const toast = el("toast");
  el("toastText").textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 3500);
}

function countSeverity(alerts) {
  return alerts.reduce((counts, alert) => {
    if (counts[alert.severity] !== undefined) counts[alert.severity] += 1;
    return counts;
  }, { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 });
}

function severityBadge(level) {
  return `<span class="severity-badge ${String(level).toLowerCase()}">${escapeHtml(level)}</span>`;
}

function formatDate(value, short = false) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || "-");
  return new Intl.DateTimeFormat("en-GB", short
    ? { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
  ).format(date);
}

function formatScore(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function number(value) {
  return new Intl.NumberFormat("en-US").format(value || 0);
}

function compactNumber(value) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value || 0);
}

function titleCase(value) {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function shortBlock(value) {
  const text = String(value);
  return text.length > 19 ? `${text.slice(0, 17)}...` : text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeDownloadName(name) {
  return String(name).replace(/[^a-z0-9._-]/gi, "_");
}

function downloadCsv(rows, filename) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [
    headers.map(quote).join(","),
    ...rows.map((row) => headers.map((header) => quote(row[header])).join(",")),
  ].join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}
