function textToPrice(t) {
  if (!t) return null;
  const m = String(t).replace(/,/g, "").match(/\$?\s*([0-9]+(?:\.[0-9]{1,2})?)/);
  return m ? parseFloat(m[1]) : null;
}

const PRICE_SELECTORS = [
  "div.product-price_component_price-lead__vlm8f",
  '[data-testid="price-dollars"]',
  '[data-testid="product-price"]',
  '[class*="product-price"]',
  '[class*="price"]'
];

const UNIT_SELECTORS = [
  '[data-testid="unit-price"]',
  '[class*="unit-price"]',
  '[class*="unit"]'
];

function findFirstText(selectors) {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent) {
      const txt = el.textContent.trim();
      if (txt) return txt;
    }
  }
  return null;
}

function fallbackPriceScan() {
  const title = document.querySelector("h1") || document.querySelector('[data-testid="product-title"]');
  const scope = title?.closest("main") || document.body;
  const text = scope ? scope.innerText : document.body.innerText;
  const m = text.match(/\$\s*([0-9]+(?:\.[0-9]{2})?)/);
  return m ? parseFloat(m[1]) : null;
}

function tryExtractPrice() {
  const priceText = findFirstText(PRICE_SELECTORS);
  const unitText = findFirstText(UNIT_SELECTORS);

  let price = textToPrice(priceText);
  if (price === null) {
    price = fallbackPriceScan();
  }

  return {
    price,
    unit_price: textToPrice(unitText),
    was_price: null,
    promo_text: null,
  };
}

async function attemptCaptureWithRetries(maxAttempts = 3) {
  const url = window.location.href;
  if (!url.includes("/shop/productdetails/") && !url.includes("/shop/product")) {
    return;
  }

  for (let i = 0; i < maxAttempts; i += 1) {
    const data = tryExtractPrice();
    if (data.price !== null) {
      chrome.runtime.sendMessage({ type: "PRICEWATCH_CAPTURE", ...data });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }

  chrome.runtime.sendMessage({ type: "PRICEWATCH_CAPTURE_FAIL", reason: "no_price_found" });
}

attemptCaptureWithRetries();
