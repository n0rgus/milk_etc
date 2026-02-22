function parseDollarAmount(text) {
  if (!text) return null;
  const s = String(text).replace(/\s+/g, " ").trim();
  const m = s.match(/\$\s*([0-9]+(?:\.[0-9]{1,2})?)/);
  if (!m) return null;
  const val = parseFloat(m[1]);
  return Number.isFinite(val) ? val : null;
}

function parseUnitDollarAmount(text) {
  if (!text) return null;
  const s = String(text).replace(/\s+/g, " ").trim();
  const m = s.match(/\$\s*([0-9]+(?:\.[0-9]{1,2})?)\s*\/\s*/);
  if (!m) return null;
  const val = parseFloat(m[1]);
  return Number.isFinite(val) ? val : null;
}

function getText(selector) {
  const el = document.querySelector(selector);
  if (!el) return null;
  return (el.textContent || "").trim();
}

function findPrice(selectors) {
  for (const sel of selectors) {
    const t = getText(sel);
    const p = parseDollarAmount(t);
    if (p !== null) return p;
  }
  return null;
}

function findUnitPrice(selectors) {
  for (const sel of selectors) {
    const t = getText(sel);
    const p = parseUnitDollarAmount(t);
    if (p !== null) return p;
  }
  return null;
}

function resolveStoreContext() {
  const host = window.location.hostname;
  const url = window.location.href;

  if (host.includes("woolworths.com.au")) {
    if (!url.includes("/shop/productdetails/")) return null;
    return {
      store: "WOOLWORTHS",
      priceSelectors: [
        "div.product-price_component_price-lead__vlm8f",
        "div.sr-only#product-price-sr",
        '[aria-labelledby="product-price-sr"]'
      ],
      unitSelectors: [
        "div.product-unit-price_component_price-cup-string__HdxP0",
        "div.sr-only#cup-price-sr",
        '[aria-labelledby="cup-price-sr"]'
      ]
    };
  }

  if (host.includes("coles.com.au")) {
    if (!url.includes("/product/")) return null;
    return {
      store: "COLES",
      priceSelectors: [
        'span.price__value[data-testid="pricing"]',
        '[data-testid="pricing"]'
      ],
      unitSelectors: [
        '[data-testid="unitPricing"]',
        'span.unit-price'
      ]
    };
  }

  return null;
}

function attemptCapture() {
  const context = resolveStoreContext();
  if (!context) return;

  const price = findPrice(context.priceSelectors);
  const unitPrice = findUnitPrice(context.unitSelectors);

  if (price !== null) {
    chrome.runtime.sendMessage({
      type: "PRICEWATCH_CAPTURE",
      store: context.store,
      price,
      unit_price: unitPrice ?? null,
      was_price: null,
      promo_text: null
    });
    return;
  }

  chrome.runtime.sendMessage({
    type: "PRICEWATCH_CAPTURE_FAIL",
    store: context.store,
    reason: "no_price_found",
    url: window.location.href
  });
}

setTimeout(attemptCapture, 900);
setTimeout(attemptCapture, 2000);
setTimeout(attemptCapture, 3500);
setTimeout(attemptCapture, 5500);
