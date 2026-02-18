from __future__ import annotations

import re
from typing import Dict, Any, List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Your provided selectors (price lead elements)
SELECTORS = {
    "WOOLWORTHS": {
        "price": 'div.product-price_component_price-lead__vlm8f',
        # optional future: "was_price": "...",
        # optional future: "promo_text": "...",
    },
    "COLES": {
        "price": 'span.price__value[data-testid="pricing"]',
    },
    "ALDI": {
        "price": "span.base-price__regular span",
    },
}

_PRICE_RE = re.compile(r"([0-9]+(?:\.[0-9]{1,2})?)")

def _parse_price(text: str) -> float | None:
    if not text:
        return None
    m = _PRICE_RE.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def scrape_item_prices(store_links: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    store_links: list of StoreLink rows (must have .store.name and .url)
    Returns: {STORE_NAME: {"price": float, "was_price": float|None, ...}}
    """
    results: Dict[str, Dict[str, Any]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        for sl in store_links:
            store_name = sl.store.name
            url = (sl.url or "").strip()
            if not url:
                continue

            sel = SELECTORS.get(store_name, {})
            price_sel = sel.get("price")
            if not price_sel:
                continue

            page = context.new_page()
            data: Dict[str, Any] = {
                "price": None,
                "was_price": None,
                "unit_price": None,
                "promo_text": None,
                "discount_percent": None,
                "url": url,
            }
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_selector(price_sel, timeout=20000)
                price_text = page.locator(price_sel).first.inner_text().strip()
                price = _parse_price(price_text)
                data["price"] = price

                # Optional: was price / promo (only if selectors are later added)
                was_sel = sel.get("was_price")
                if was_sel:
                    try:
                        was_text = page.locator(was_sel).first.inner_text().strip()
                        data["was_price"] = _parse_price(was_text)
                    except Exception:
                        pass

                promo_sel = sel.get("promo_text")
                if promo_sel:
                    try:
                        data["promo_text"] = page.locator(promo_sel).first.inner_text().strip()
                    except Exception:
                        pass

                # Compute discount
                if data.get("price") is not None and data.get("was_price") is not None and data["was_price"] > 0:
                    data["discount_percent"] = round((data["was_price"] - data["price"]) / data["was_price"] * 100.0, 1)

            except PlaywrightTimeoutError:
                data["promo_text"] = (data.get("promo_text") or "") + " [timeout]"
            except Exception as e:
                data["promo_text"] = (data.get("promo_text") or "") + f" [error: {type(e).__name__}]"
            finally:
                page.close()

            results[store_name] = data

        context.close()
        browser.close()

    return results
