const DEFAULTS = {
  appBase: "http://127.0.0.1:8000"
};

let session = null;
// session = { originTabId, itemId, name, stores:Set, openedTabs:Set, completed:Set }

function storeSearchUrl(store, query) {
  const q = encodeURIComponent(query || "");
  if (store === "WOOLWORTHS") return `https://www.woolworths.com.au/shop/search/products?searchTerm=${q}`;
  if (store === "COLES") return `https://www.coles.com.au/search?q=${q}`;
  if (store === "ALDI") return `https://www.aldi.com.au/en/search/?q=${q}`;
  return null;
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
        openedTabs: new Set(),
        completed: new Set()
      };

      for (const store of session.stores) {
        const url = storeSearchUrl(store, name);
        if (!url) continue;
        const tab = await chrome.tabs.create({ url, active: false });
        session.openedTabs.add(tab.id);
      }

      // bring origin tab back to front
      await chrome.tabs.update(originTabId, { active: true });
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === "LH_PRODUCT_PAGE") {
      if (!session) {
        sendResponse({ ok: false, error: "no_session" });
        return;
      }

      const { store, url, label } = msg;
      if (!session.stores.has(store)) {
        sendResponse({ ok: false, error: "store_not_in_session" });
        return;
      }

      // Fill back into origin tab form
      await chrome.tabs.sendMessage(session.originTabId, {
        type: "LH_FILL",
        store,
        url,
        label
      });

      session.completed.add(store);

      // If we've completed all requested stores, close search tabs and end session
      if (session.completed.size >= session.stores.size) {
        for (const tabId of session.openedTabs) {
          try { await chrome.tabs.remove(tabId); } catch {}
        }
        session = null;
      } else {
        // switch back to origin tab after each capture
        await chrome.tabs.update(session.originTabId, { active: true });
      }

      sendResponse({ ok: true });
      return;
    }
  })().catch((e) => {
    console.warn("Link Helper background error:", e);
    try { sendResponse({ ok: false, error: String(e) }); } catch {}
  });

  return true;
});
