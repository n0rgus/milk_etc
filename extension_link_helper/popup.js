async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function setStatus(msg, cls) {
  const el = document.getElementById("status");
  el.className = "small " + (cls || "");
  el.textContent = msg;
}

async function requestContextFromAppTab(tabId) {
  const resp = await chrome.tabs.sendMessage(tabId, { type: "LH_GET_CONTEXT" });
  return resp;
}

async function openSearches(stores) {
  const tab = await getActiveTab();
  if (!tab?.id) return;

  const ctx = await requestContextFromAppTab(tab.id);
  if (!ctx?.ok) {
    setStatus("Open this popup while on an item edit page: /items/<id>", "warn");
    return;
  }

  document.getElementById("productName").textContent = ctx.name || "(blank)";

  const res = await chrome.runtime.sendMessage({
    type: "LH_START",
    originTabId: tab.id,
    itemId: ctx.itemId,
    name: ctx.name,
    stores
  });

  if (res?.ok) setStatus("Store tabs ready. Pick results and capture/focus as needed.", "ok");
  else setStatus("Failed to start.", "warn");
}

async function captureActiveTab() {
  const res = await chrome.runtime.sendMessage({ type: "LH_CAPTURE_ACTIVE_TAB" });
  if (res?.ok) setStatus("Captured active tab and filled edit form.", "ok");
  else setStatus(`Capture failed: ${res?.error || "unknown"}`, "warn");
}

async function focusOrigin() {
  const res = await chrome.runtime.sendMessage({ type: "LH_FOCUS_ORIGIN" });
  if (res?.ok) setStatus("Focused edit page tab.", "ok");
  else setStatus(`Focus failed: ${res?.error || "unknown"}`, "warn");
}

async function rerunSearchActive() {
  const res = await chrome.runtime.sendMessage({ type: "LH_RERUN_SEARCH_ACTIVE" });
  if (res?.ok) setStatus("Re-ran search in active store tab.", "ok");
  else setStatus(`Re-run failed: ${res?.error || "unknown"}`, "warn");
}

document.addEventListener("DOMContentLoaded", async () => {
  const versionEl = document.getElementById("version");
  if (versionEl) {
    versionEl.textContent = `Extension v${chrome.runtime.getManifest().version}`;
  }
  try {
    const tab = await getActiveTab();
    if (!tab?.id) return;
    const ctx = await requestContextFromAppTab(tab.id);
    document.getElementById("productName").textContent = ctx?.name || "—";
  } catch {
    document.getElementById("productName").textContent = "—";
  }

  document.getElementById("openAll").addEventListener("click", () => openSearches(["ALDI", "COLES", "WOOLWORTHS"]));
  document.getElementById("openAldi").addEventListener("click", () => openSearches(["ALDI"]));
  document.getElementById("openColes").addEventListener("click", () => openSearches(["COLES"]));
  document.getElementById("openWoolies").addEventListener("click", () => openSearches(["WOOLWORTHS"]));
  document.getElementById("captureActive").addEventListener("click", captureActiveTab);
  document.getElementById("focusOrigin").addEventListener("click", focusOrigin);
  document.getElementById("rerunSearch").addEventListener("click", rerunSearchActive);
});
