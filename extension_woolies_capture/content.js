function textToPrice(t) {
  if (!t) return null;
  const m = String(t).replace(",", "").match(/([0-9]+(?:\.[0-9]{1,2})?)/);
  return m ? parseFloat(m[1]) : null;
}

const PRICE_SELECTORS = [
  "div.product-price_component_price-lead__vlm8f",
  '[data-testid="price-dollars"]',
  '[data-testid="product-price"]',
  '[class*="price"]'
];

const UNIT_SELECTORS = [
  '[data-testid="unit-price"]',
  '[class*="unit"]'
];

function findFirstText(selectors) {
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent) {
      return el.textContent.trim();
    }
  }
  return null;
}

function attemptCapture() {
  const url = window.location.href;
  if (!url.includes("/shop/productdetails/") && !url.includes("/shop/product")) {
    return;
  }

  const priceText = findFirstText(PRICE_SELECTORS);
  const unitText = findFirstText(UNIT_SELECTORS);

  const price = textToPrice(priceText);
  const unit_price = textToPrice(unitText);

  if (price !== null) {
    chrome.runtime.sendMessage({
      type: "PRICEWATCH_CAPTURE",
      price,
      unit_price,
      was_price: null,
      promo_text: null
    });
  }
}

setTimeout(attemptCapture, 800);
setTimeout(attemptCapture, 1800);
setTimeout(attemptCapture, 3000);
