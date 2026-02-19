function parseDollarAmount(text) {
  if (!text) return null;
  const s = String(text).replace(/\s+/g, " ").trim();

  // Require $ to avoid capturing pack sizes, grams, etc.
  const m = s.match(/\$\s*([0-9]+(?:\.[0-9]{1,2})?)/);
  if (!m) return null;

  const val = parseFloat(m[1]);
  return Number.isFinite(val) ? val : null;
}

function parseUnitDollarAmount(text) {
  if (!text) return null;
  const s = String(text).replace(/\s+/g, " ").trim();

  // Unit price format example: "$1.55 / 1L" or "$2.20 / 100g"
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

// Strong selectors from the provided Woolies PDP markup
const PRICE_SELECTOR_STRONG = "div.product-price_component_price-lead__vlm8f";
const UNIT_SELECTOR_STRONG = "div.product-unit-price_component_price-cup-string__HdxP0";

// Fallbacks (still safe because parsing requires $)
const PRICE_SELECTORS_FALLBACK = [
  PRICE_SELECTOR_STRONG,
  // sometimes price is available via sr-only text:
  "div.sr-only#product-price-sr",
  '[aria-labelledby="product-price-sr"]'
];

const UNIT_SELECTORS_FALLBACK = [
  UNIT_SELECTOR_STRONG,
  "div.sr-only#cup-price-sr",
  '[aria-labelledby="cup-price-sr"]'
];

function findPrice() {
  for (const sel of PRICE_SELECTORS_FALLBACK) {
    const t = getText(sel);
    const p = parseDollarAmount(t);
    if (p !== null) return p;
  }
  return null;
}

function findUnitPrice() {
  for (const sel of UNIT_SELECTORS_FALLBACK) {
    const t = getText(sel);
    const u = parseUnitDollarAmount(t);
    if (u !== null) return u;
  }
  return null;
}

function attemptCapture() {
  const url = window.location.href;

  // Only attempt on product detail pages
  if (!url.includes("/shop/productdetails/")) return;

  const price = findPrice();
  const unit_price = findUnitPrice();

  if (price !== null) {
    chrome.runtime.sendMessage({
      type: "PRICEWATCH_CAPTURE",
      price,
      unit_price: unit_price ?? null,
      was_price: null,
      promo_text: null
    });
  } else {
    chrome.runtime.sendMessage({
      type: "PRICEWATCH_CAPTURE_FAIL",
      reason: "no_price_found",
      url
    });
  }
}

// SPA hydration timing: try a few times
setTimeout(attemptCapture, 900);
setTimeout(attemptCapture, 2000);
setTimeout(attemptCapture, 3500);
setTimeout(attemptCapture, 5500);
