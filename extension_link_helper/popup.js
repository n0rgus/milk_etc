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

  if (res?.ok) setStatus("Opened search tabs. Pick a result in each store tab.", "ok");
  else setStatus("Failed to start.", "warn");
}

document.addEventListener("DOMContentLoaded", async () => {
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
});
