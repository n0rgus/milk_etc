from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Directories for persistent browser state and debug artifacts
STATE_DIR = Path(os.environ.get("PRICEWATCH_STATE_DIR", "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_DIR = Path(os.environ.get("PRICEWATCH_DEBUG_DIR", "scrape_debug"))
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def state_path(store_name: str) -> str:
    return str(STATE_DIR / f"{store_name.lower()}.json")

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

        ctx_kwargs = {}

        # Load saved storage state if available
        sp = state_path(store_links[0].store.name) if store_links else None
        if sp and Path(sp).exists():
            ctx_kwargs["storage_state"] = sp

        # Optional geolocation (Melbourne default, override with env vars)
        lat = float(os.environ.get("PRICEWATCH_GEO_LAT", "-37.8136"))
        lon = float(os.environ.get("PRICEWATCH_GEO_LON", "144.9631"))

        ctx_kwargs["geolocation"] = {"latitude": lat, "longitude": lon}

        context = browser.new_context(**ctx_kwargs)

        # Grant geolocation permission
        try:
            context.grant_permissions(["geolocation"], origin="https://www.coles.com.au")
            context.grant_permissions(["geolocation"], origin="https://www.woolworths.com.au")
        except Exception:
            pass

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

                matched = page.locator(price_sel).count()
                if matched == 0:
                    page.screenshot(
                        path=str(DEBUG_DIR / f"{store_name.lower()}_no_match.png"),
                        full_page=True,
                    )
                    (DEBUG_DIR / f"{store_name.lower()}_no_match.html").write_text(
                        page.content(), encoding="utf-8"
                    )
                    raise Exception(f"No elements matched selector: {price_sel}")

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
                try:
                    page.screenshot(
                        path=str(DEBUG_DIR / f"{store_name.lower()}_error.png"),
                        full_page=True,
                    )
                    (DEBUG_DIR / f"{store_name.lower()}_error.html").write_text(
                        page.content(), encoding="utf-8"
                    )
                except Exception:
                    pass
                data["promo_text"] = (data.get("promo_text") or "") + f" [error: {type(e).__name__}]"
            finally:
                page.close()

            results[store_name] = data

            try:
                context.storage_state(path=state_path(store_name))
            except Exception:
                pass

        context.close()
        browser.close()

    return results
