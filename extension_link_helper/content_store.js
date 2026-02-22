function detectStore() {
  const h = location.hostname;
  if (h.includes("woolworths.com.au")) return "WOOLWORTHS";
  if (h.includes("coles.com.au")) return "COLES";
  if (h.includes("aldi.com.au")) return "ALDI";
  return null;
}

function isProductPage(store) {
  const url = location.href;
  if (store === "WOOLWORTHS") return url.includes("/shop/productdetails/");
  if (store === "COLES") return url.includes("/product/");
  if (store === "ALDI") {
    // Aldi varies; treat pages with "/p/" or a product-like pattern as candidates
    return url.includes("/p/") || url.includes("/product");
  }
  return false;
}

function getLabel(store) {
  // Best-effort: keep short and robust. Title tag is a decent fallback.
  const tryText = (sel) => {
    const el = document.querySelector(sel);
    return el ? (el.textContent || "").trim() : null;
  };

  if (store === "WOOLWORTHS") {
    return (
      tryText('h1[data-testid="product-title"]') ||
      tryText("h1") ||
      document.title
    );
  }
  if (store === "COLES") {
    return (
      tryText('h1[data-testid="product-title"]') ||
      tryText("h1") ||
      document.title
    );
  }
  if (store === "ALDI") {
    return tryText("h1") || document.title;
  }
  return document.title;
}

async function maybeCapture() {
  const store = detectStore();
  if (!store) return;
  if (!isProductPage(store)) return;

  // Only act if a linking session is active (background tracks this)
  chrome.runtime.sendMessage({
    type: "LH_PRODUCT_PAGE",
    store,
    url: location.href,
    label: getLabel(store)
  });
}

// Give SPA time to settle
setTimeout(maybeCapture, 1200);
setTimeout(maybeCapture, 2500);
