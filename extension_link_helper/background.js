const DEFAULTS = {
  appBase: "http://127.0.0.1:8000"
};

const STORE_ENTRY_URLS = {
  WOOLWORTHS: "https://www.woolworths.com.au/shop/search/products",
  COLES: "https://www.coles.com.au/search",
  ALDI: "https://www.aldi.com.au/en/search/"
};

let session = null;
// session = {
//   originTabId, itemId, name,
//   stores:Set,
//   storeTabIds:{ ALDI, COLES, WOOLWORTHS },
//   completed:Set
// }

async function upsertStoreTab(store) {
  const existingTabId = session?.storeTabIds?.[store];
  if (existingTabId) {
    try {
      const tab = await chrome.tabs.get(existingTabId);
      return tab;
    } catch {
      // Tab was closed; create a new one below.
    }
  }

  const tab = await chrome.tabs.create({
    url: STORE_ENTRY_URLS[store],
    active: false
  });

  session.storeTabIds[store] = tab.id;
  return tab;
}

async function runStoreSearch(store, query) {
  const tab = await upsertStoreTab(store);
  await chrome.tabs.update(tab.id, { url: STORE_ENTRY_URLS[store], active: false });

  try {
    await chrome.tabs.sendMessage(tab.id, {
      type: "LH_DO_SEARCH",
      store,
      query
    });
  } catch {
    // Content script can race with navigation; retry once after a short delay.
    await new Promise((resolve) => setTimeout(resolve, 700));
    await chrome.tabs.sendMessage(tab.id, {
      type: "LH_DO_SEARCH",
      store,
      query
    });
  }
}

async function fillOriginFromStorePage(pageInfo) {
  if (!session) return { ok: false, error: "no_session" };

  const { store, url, label } = pageInfo;
  if (!session.stores.has(store)) return { ok: false, error: "store_not_in_session" };

  await chrome.tabs.sendMessage(session.originTabId, {
    type: "LH_FILL",
    store,
    url,
    label
  });

  session.completed.add(store);

  try {
    await chrome.tabs.update(session.originTabId, { active: true });
  } catch {
    // origin tab may be gone; ignore.
  }

  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg?.type === "LH_START") {
      const { originTabId, itemId, name, stores } = msg;
      session = {
        originTabId,
        itemId,
        name,
        stores: new Set(stores || []),
        storeTabIds: {},
        completed: new Set()
      };

      for (const store of session.stores) {
        if (!STORE_ENTRY_URLS[store]) continue;
        await runStoreSearch(store, name);
      }

      await chrome.tabs.update(originTabId, { active: true });
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "LH_PRODUCT_PAGE") {
      const res = await fillOriginFromStorePage(msg);
      sendResponse(res);
      return;
    }

    if (msg?.type === "LH_CAPTURE_ACTIVE_TAB") {
      if (!session) {
        sendResponse({ ok: false, error: "no_session" });
        return;
      }

      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!activeTab?.id) {
        sendResponse({ ok: false, error: "no_active_tab" });
        return;
      }

      const info = await chrome.tabs.sendMessage(activeTab.id, { type: "LH_GET_PAGE_INFO" });
      if (!info?.ok || !info?.store) {
        sendResponse({ ok: false, error: "not_store_page" });
        return;
      }

      const res = await fillOriginFromStorePage(info);
      sendResponse(res);
      return;
    }

    if (msg?.type === "LH_FOCUS_ORIGIN") {
      if (!session?.originTabId) {
        sendResponse({ ok: false, error: "no_session" });
        return;
      }
      await chrome.tabs.update(session.originTabId, { active: true });
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "LH_RERUN_SEARCH_ACTIVE") {
      if (!session) {
        sendResponse({ ok: false, error: "no_session" });
        return;
      }

      const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!activeTab?.id) {
        sendResponse({ ok: false, error: "no_active_tab" });
        return;
      }

      const info = await chrome.tabs.sendMessage(activeTab.id, { type: "LH_GET_PAGE_INFO" });
      if (!info?.store || !session.stores.has(info.store)) {
        sendResponse({ ok: false, error: "active_tab_not_session_store" });
        return;
      }

      await chrome.tabs.sendMessage(activeTab.id, {
        type: "LH_DO_SEARCH",
        store: info.store,
        query: session.name
      });
      sendResponse({ ok: true });
      return;
    }
  })().catch((e) => {
    console.warn("Link Helper background error:", e);
    try {
      sendResponse({ ok: false, error: String(e) });
    } catch {}
  });

  return true;
});
