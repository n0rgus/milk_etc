const DEFAULT_APP_BASE = "http://127.0.0.1:8000";
const DEFAULT_MODE = "WOOLWORTHS";

const modeEl = document.getElementById("mode");
const appBaseEl = document.getElementById("appBase");
const startStopBtn = document.getElementById("startStopBtn");
const statusEl = document.getElementById("status");

(async function init() {
  const data = await chrome.storage.local.get(["mode", "appBase"]);
  modeEl.value = data.mode || DEFAULT_MODE;
  appBaseEl.value = data.appBase || DEFAULT_APP_BASE;

  modeEl.addEventListener("change", saveConfig);
  appBaseEl.addEventListener("change", saveConfig);
  startStopBtn.addEventListener("click", toggleRun);

  await refreshStatus();
})();

async function saveConfig() {
  await chrome.storage.local.set({
    mode: modeEl.value,
    appBase: (appBaseEl.value || DEFAULT_APP_BASE).trim() || DEFAULT_APP_BASE
  });
}

async function toggleRun() {
  await saveConfig();
  const status = await getBackgroundStatus();

  if (status.running) {
    await chrome.runtime.sendMessage({ type: "PRICEWATCH_STOP" });
    await refreshStatus();
    return;
  }

  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!activeTab?.id) {
    statusEl.textContent = "No active tab found.";
    return;
  }

  await chrome.runtime.sendMessage({ type: "PRICEWATCH_START", tabId: activeTab.id });
  await refreshStatus();
}

async function refreshStatus() {
  const status = await getBackgroundStatus();

  if (status.running) {
    startStopBtn.textContent = "Stop";
    startStopBtn.classList.remove("start");
    startStopBtn.classList.add("stop");
    if (status.currentJob) {
      statusEl.textContent = `Capturing ${status.currentJob.store}: ${status.currentJob.item_name || status.currentJob.item_id}`;
    } else {
      statusEl.textContent = "Capturing...";
    }
  } else {
    startStopBtn.textContent = "Start";
    startStopBtn.classList.remove("stop");
    startStopBtn.classList.add("start");
    statusEl.textContent = "Idle.";
  }
}

async function getBackgroundStatus() {
  try {
    return await chrome.runtime.sendMessage({ type: "PRICEWATCH_STATUS" });
  } catch (err) {
    return { running: false, currentJob: null };
  }
}
