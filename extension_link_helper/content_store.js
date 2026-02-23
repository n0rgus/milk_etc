function detectStore() {
  const h = location.hostname;
  if (h.includes("woolworths.com.au")) return "WOOLWORTHS";
  if (h.includes("coles.com.au")) return "COLES";
  if (h.includes("aldi.com.au")) return "ALDI";
  return null;
}

function isProductPage(store) {
  const url = location.href;

  if (store === "WOOLWORTHS") {
    return (
      url.includes("/shop/productdetails/") ||
      url.includes("/productdetails/") ||
      /\/shop\/productdetails\/\d+/i.test(url)
    );
  }

  if (store === "COLES") {
    return (
      url.includes("/product/") ||
      /\/product\/[^/?#]+/i.test(url) ||
      document.querySelector('meta[property="og:type"][content="product"]')
    );
  }

  if (store === "ALDI") {
    return (
      url.includes("/p/") ||
      url.includes("/product") ||
      /\/product\//i.test(url)
    );
  }

  return false;
}

function getLabel(store) {
  const tryText = (sel) => {
    const el = document.querySelector(sel);
    return el ? (el.textContent || "").trim() : null;
  };

  if (store === "WOOLWORTHS") {
    return (
      tryText('h1[data-testid="product-title"]') ||
      tryText('h1[data-testid="productName"]') ||
      tryText("main h1") ||
      tryText("h1") ||
      document.title
    );
  }

  if (store === "COLES") {
    return (
      tryText('h1[data-testid="product-title"]') ||
      tryText("main h1") ||
      tryText("h1") ||
      document.title
    );
  }

  if (store === "ALDI") {
    return tryText("main h1") || tryText("h1") || document.title;
  }

  return document.title;
}

function doAldiSearch(query) {
  const input =
    document.querySelector('input[type="search"]') ||
    document.querySelector('input[name="q"]') ||
    document.querySelector('input[name*="q" i]') ||
    document.querySelector('input[placeholder*="Search" i]');

  if (!input) return false;

  input.focus();
  input.value = query || "";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));

  const form = input.closest("form");
  if (form) {
    form.submit();
    return true;
  }

  input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true }));
  input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", code: "Enter", bubbles: true }));
  return true;
}

function doWooliesSearch(query) {
  const q = encodeURIComponent(query || "");
  location.href = `https://www.woolworths.com.au/shop/search/products?searchTerm=${q}`;
}

function doColesSearch(query) {
  const q = encodeURIComponent(query || "");
  location.href = `https://www.coles.com.au/search?q=${q}`;
}

let lastCaptureKey = "";

function maybeCapture() {
  const store = detectStore();
  if (!store) return;
  if (!isProductPage(store)) return;

  const label = getLabel(store);
  const captureKey = `${store}|${location.href}|${label}`;
  if (captureKey === lastCaptureKey) return;
  lastCaptureKey = captureKey;

  chrome.runtime.sendMessage({
    type: "LH_PRODUCT_PAGE",
    store,
    url: location.href,
    label
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg?.type === "LH_DO_SEARCH") {
      const store = detectStore();
      const query = msg.query || "";

      if (!store) {
        sendResponse({ ok: false, error: "store_not_detected" });
        return;
      }

      if (store === "ALDI") {
        sendResponse({ ok: doAldiSearch(query) });
        return;
      }

      if (store === "WOOLWORTHS") {
        doWooliesSearch(query);
        sendResponse({ ok: true });
        return;
      }

      if (store === "COLES") {
        doColesSearch(query);
        sendResponse({ ok: true });
        return;
      }

      sendResponse({ ok: false, error: "unsupported_store" });
      return;
    }

    if (msg?.type === "LH_GET_PAGE_INFO") {
      const store = detectStore();
      sendResponse({
        ok: !!store,
        store,
        url: location.href,
        label: store ? getLabel(store) : document.title,
        isProduct: store ? !!isProductPage(store) : false
      });
      return;
    }
  })().catch((e) => {
    sendResponse({ ok: false, error: String(e) });
  });

  return true;
});

setTimeout(maybeCapture, 800);
setTimeout(maybeCapture, 1500);
setTimeout(maybeCapture, 2800);
setTimeout(maybeCapture, 5000);

const observer = new MutationObserver(() => {
  maybeCapture();
});

observer.observe(document.documentElement, { childList: true, subtree: true });
setTimeout(() => observer.disconnect(), 15000);
