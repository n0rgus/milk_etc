const APP_BASE = "http://127.0.0.1:8000";
const STORE = "WOOLWORTHS";

let running = false;
let activeTabId = null;
let currentJob = null;

chrome.action.onClicked.addListener(async (tab) => {
  if (running) {
    running = false;
    currentJob = null;
    activeTabId = null;
    console.log("[PriceWatch] stopped");
    return;
  }

  running = true;
  activeTabId = tab.id;
  currentJob = null;
  console.log("[PriceWatch] starting…");
  await nextAndNavigate();
});

async function nextAndNavigate() {
  if (!running || !activeTabId) return;

  const next = await fetchJson(`${APP_BASE}/api/next?store=${STORE}`);
  if (!next || next.done) {
    console.log("[PriceWatch] done (no more items)");
    running = false;
    currentJob = null;
    return;
  }

  currentJob = next;
  console.log("[PriceWatch] next:", currentJob.item_name, currentJob.url);
  await chrome.tabs.update(activeTabId, { url: currentJob.url });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (!running) return;

    if (msg && msg.type === "PRICEWATCH_CAPTURE" && currentJob) {
      if (sender.tab && sender.tab.id !== activeTabId) return;

      const payload = {
        capture_run_id: currentJob.capture_run_id,
        store: STORE,
        item_id: currentJob.item_id,
        url: currentJob.url,
        price: msg.price,
        unit_price: msg.unit_price ?? null,
        was_price: msg.was_price ?? null,
        promo_text: msg.promo_text ?? null
      };

      const res = await fetch(`${APP_BASE}/api/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        console.warn("[PriceWatch] capture POST failed:", res.status);
      }

      await sleep(800);
      await nextAndNavigate();
    }

    if (msg && msg.type === "PRICEWATCH_CAPTURE_FAIL") {
      console.warn("[PriceWatch] capture fail:", msg.reason || "unknown");
      await sleep(800);
      await nextAndNavigate();
    }
  })();

  sendResponse({ ok: true });
  return true;
});

async function fetchJson(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.warn("[PriceWatch] fetchJson error:", e);
    return null;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
