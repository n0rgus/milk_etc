const DEFAULT_APP_BASE = "http://127.0.0.1:8000";
const DEFAULT_MODE = "WOOLWORTHS";

let running = false;
let activeTabId = null;
let currentJob = null;

function modeToStores(mode) {
  switch (mode) {
    case "COLES":
      return ["COLES"];
    case "SEQ_WC":
      return ["WOOLWORTHS", "COLES"];
    case "SEQ_CW":
      return ["COLES", "WOOLWORTHS"];
    case "WOOLWORTHS":
    default:
      return ["WOOLWORTHS"];
  }
}

async function getConfig() {
  const data = await chrome.storage.local.get(["mode", "appBase"]);
  const appBase = (data.appBase || DEFAULT_APP_BASE).trim() || DEFAULT_APP_BASE;
  const mode = data.mode || DEFAULT_MODE;
  return { appBase, mode, stores: modeToStores(mode) };
}

async function startCapture(tabId) {
  running = true;
  activeTabId = tabId;
  currentJob = null;
  console.log("[PriceWatch] starting...");
  await nextAndNavigate();
}

function stopCapture() {
  running = false;
  activeTabId = null;
  currentJob = null;
  console.log("[PriceWatch] stopped");
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg?.type === "PRICEWATCH_START") {
      let tabId = msg.tabId;
      if (!tabId) {
        const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
        tabId = active?.id;
      }
      if (tabId) {
        await startCapture(tabId);
      }
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "PRICEWATCH_STOP") {
      stopCapture();
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "PRICEWATCH_STATUS") {
      sendResponse({ ok: true, running, currentJob });
      return;
    }

    if (!running) {
      sendResponse({ ok: true, ignored: true });
      return;
    }

    if (msg?.type === "PRICEWATCH_CAPTURE" && currentJob) {
      if (sender.tab && sender.tab.id !== activeTabId) {
        sendResponse({ ok: true, ignored: true });
        return;
      }

      const { appBase } = await getConfig();
      const payload = {
        capture_run_id: currentJob.capture_run_id,
        store: currentJob.store,
        item_id: currentJob.item_id,
        url: currentJob.url,
        price: msg.price,
        unit_price: msg.unit_price ?? null,
        was_price: msg.was_price ?? null,
        promo_text: msg.promo_text ?? null
      };

      try {
        const res = await fetch(`${appBase}/api/capture`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          console.warn("[PriceWatch] capture POST failed:", res.status);
        }
      } catch (err) {
        console.warn("[PriceWatch] capture POST error:", err);
      }

      await sleep(800);
      await nextAndNavigate();
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "PRICEWATCH_CAPTURE_FAIL") {
      console.warn("[PriceWatch] capture failed:", msg.reason || "unknown", msg.url || "", msg.store || "");
      await sleep(800);
      await nextAndNavigate();
      sendResponse({ ok: true });
      return;
    }

    sendResponse({ ok: true, ignored: true });
  })();

  return true;
});

async function nextAndNavigate() {
  if (!running || !activeTabId) return;

  const { appBase, stores } = await getConfig();
  const next = await fetchNextJob(appBase, stores);

  if (!next || next.done) {
    console.log("[PriceWatch] done (no more items)");
    stopCapture();
    return;
  }

  currentJob = next;
  console.log("[PriceWatch] next:", currentJob.store, currentJob.item_name, currentJob.url);

  try {
    await chrome.tabs.update(activeTabId, { url: currentJob.url });
  } catch (err) {
    console.warn("[PriceWatch] tab update failed:", err);
    stopCapture();
  }
}

async function fetchNextJob(appBase, stores) {
  const storesParam = stores.join(",");
  const nextMultiUrl = `${appBase}/api/next_multi?stores=${encodeURIComponent(storesParam)}`;
  const multiRes = await fetchJsonWithStatus(nextMultiUrl);

  if (multiRes.ok) {
    return multiRes.data;
  }

  for (const store of stores) {
    const data = await fetchJson(`${appBase}/api/next?store=${encodeURIComponent(store)}`);
    if (data && !data.done) {
      return data;
    }
  }

  return { done: true };
}

async function fetchJsonWithStatus(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return { ok: false, data: null };
    return { ok: true, data: await r.json() };
  } catch (e) {
    console.warn("[PriceWatch] fetchJsonWithStatus error:", e);
    return { ok: false, data: null };
  }
}

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
