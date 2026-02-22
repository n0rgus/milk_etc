function getItemIdFromPath() {
  // expects /items/<id> (optionally trailing slash)
  const parts = location.pathname.split("/").filter(Boolean);
  const idx = parts.indexOf("items");
  if (idx === -1) return null;
  const id = parts[idx + 1];
  if (!id) return null;
  return /^\d+$/.test(id) ? parseInt(id, 10) : null;
}

function getNameFromInput() {
  const el = document.getElementById("name");
  if (!el) return null;
  return (el.value || "").trim();
}

function findInputFor(store, kind) {
  // kind: "url" or "label"
  const s = store.toLowerCase();
  const k = kind.toLowerCase();

  const selectors = [
    `input#${s}_${k}`,
    `input[name="${s}_${k}"]`,
    `input[id*="${s}"][id*="${k}"]`,
    `input[name*="${s}"][name*="${k}"]`,
    `input[id*="${s}"][id*="${k}"]`,
    `textarea#${s}_${k}`,
    `textarea[name="${s}_${k}"]`,
    `textarea[id*="${s}"][id*="${k}"]`,
    `textarea[name*="${s}"][name*="${k}"]`
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function setValue(el, value) {
  if (!el) return false;
  el.focus();
  el.value = value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  try {
    if (msg?.type === "LH_GET_CONTEXT") {
      const itemId = getItemIdFromPath();
      const name = getNameFromInput();
      sendResponse({ ok: !!itemId, itemId, name });
      return true;
    }

    if (msg?.type === "LH_FILL") {
      const store = msg.store;
      const url = msg.url || "";
      const label = msg.label || "";

      const urlEl = findInputFor(store, "url");
      const labelEl = findInputFor(store, "label") || findInputFor(store, "title");

      const okUrl = setValue(urlEl, url);
      const okLabel = label ? setValue(labelEl, label) : true;

      if (!okUrl) {
        alert(`Link Helper: Could not find URL input for ${store}.\\nCaptured URL:\\n${url}`);
      }
      if (label && !okLabel) {
        // label is nice-to-have; don't hard fail
        console.warn("Link Helper: Could not find label input for", store, "label:", label);
      }

      sendResponse({ ok: okUrl, filledUrl: okUrl, filledLabel: okLabel });
      return true;
    }
  } catch (e) {
    console.warn("Link Helper error:", e);
    sendResponse({ ok: false, error: String(e) });
    return true;
  }
});
