from __future__ import annotations

import asyncio
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

STATE_DIR = Path(os.environ.get("PRICEWATCH_STATE_DIR", "state"))
STATE_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_DIR = Path(os.environ.get("PRICEWATCH_DEBUG_DIR", "scrape_debug"))
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def _state_path(store_name: str) -> str:
    return str(STATE_DIR / f"{store_name.lower()}.json")


SELECTORS = {
    "WOOLWORTHS": {
        "price": 'div.product-price_component_price-lead__vlm8f',
    },
    "COLES": {
        "price": [
            'span.price__value[data-testid="pricing"]',
            'span[data-testid="pricing"]',
            '[data-testid="pricing"] span.price__value',
        ],
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


def _selector_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _close_quietly(resource: Any) -> None:
    try:
        resource.close()
    except Exception:
        pass


def _launch_browser(playwright: Any, *, headful: bool, slowmo_ms: int):
    launch_kwargs = {
        "headless": not headful,
        "slow_mo": slowmo_ms if headful else 0,
    }
    preferred_channel = os.environ.get("PRICEWATCH_BROWSER_CHANNEL", "msedge").strip()
    if preferred_channel:
        try:
            return playwright.chromium.launch(channel=preferred_channel, **launch_kwargs)
        except Exception:
            pass
    return playwright.chromium.launch(**launch_kwargs)


def scrape_item_prices(store_links: List[Any], settings: Dict[str, Any] | None = None) -> Dict[str, Dict[str, Any]]:
    """
    store_links: list of StoreLink rows (must have .store.name and .url)
    Returns: {STORE_NAME: {"price": float, "was_price": float|None, ...}}
    """
    results: Dict[str, Dict[str, Any]] = {}
    by_store: DefaultDict[str, List[Any]] = defaultdict(list)
    for sl in store_links:
        if sl.url:
            by_store[sl.store.name].append(sl)

    settings = settings or {}
    env_headful = os.environ.get("PRICEWATCH_HEADFUL", "0").strip().lower() in ("1", "true", "yes")
    env_slowmo_ms = int(os.environ.get("PRICEWATCH_SLOWMO_MS", "0"))
    headful = bool(settings.get("headful", env_headful))
    try:
        slowmo_ms = max(0, int(settings.get("slowmo_ms", env_slowmo_ms) or 0))
    except (TypeError, ValueError):
        slowmo_ms = env_slowmo_ms
    debug_capture_enabled = bool(settings.get("debug_capture_enabled", True))
    save_storage_state = bool(settings.get("save_storage_state", True))

    with sync_playwright() as p:
        # NOTE: Coles tends to behave differently in bundled headless Chromium vs a real installed browser.
        # Using the installed Edge channel on Windows usually matches "debug headful" behaviour much better.
        browser = _launch_browser(p, headful=headful, slowmo_ms=slowmo_ms)

        for store_name, links in by_store.items():
            ctx_kwargs: Dict[str, Any] = {}
            sp = _state_path(store_name)
            if Path(sp).exists():
                ctx_kwargs["storage_state"] = sp

            lat = float(os.environ.get("PRICEWATCH_GEO_LAT", "-37.8136"))
            lon = float(os.environ.get("PRICEWATCH_GEO_LON", "144.9631"))
            ctx_kwargs["geolocation"] = {"latitude": lat, "longitude": lon}

            context = browser.new_context(**ctx_kwargs)

            try:
                if store_name == "COLES":
                    context.grant_permissions(["geolocation"], origin="https://www.coles.com.au")
            except Exception:
                pass

            for sl in links:
                url = (sl.url or "").strip()
                if not url:
                    continue

                sel = SELECTORS.get(store_name, {})
                price_selectors = _selector_list(sel.get("price"))
                if not price_selectors:
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
                    # Coles (and some SPA flows) can "half render": selector appears before final price is injected.
                    # Retry a few times with increasing waits to mirror debug/slow-mo behaviour.
                    price_text = None
                    matched_selector = None
                    for attempt in range(3):
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        except PlaywrightError as e:
                            if "Target page, context or browser has been closed" not in str(e):
                                raise
                            _close_quietly(page)
                            page = context.new_page()
                            page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2500 + attempt * 1000)

                        for price_sel in price_selectors:
                            try:
                                page.wait_for_selector(price_sel, timeout=15000)
                            except PlaywrightTimeoutError:
                                continue

                            if page.locator(price_sel).count() <= 0:
                                continue

                            txt = page.locator(price_sel).first.inner_text().strip()
                            parsed = _parse_price(txt)
                            if parsed is not None:
                                price_text = txt
                                matched_selector = price_sel
                                break

                        if price_text:
                            break

                    if price_text is None:
                        if store_name == "COLES" and debug_capture_enabled:
                            page.screenshot(path=str(DEBUG_DIR / "coles_no_match.png"), full_page=True)
                            (DEBUG_DIR / "coles_no_match.html").write_text(page.content(), encoding="utf-8")
                        raise Exception(f"No elements matched selectors: {price_selectors}")

                    data["price"] = _parse_price(price_text)

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

                    if (
                        data.get("price") is not None
                        and data.get("was_price") is not None
                        and data["was_price"] > 0
                    ):
                        data["discount_percent"] = round(
                            (data["was_price"] - data["price"]) / data["was_price"] * 100.0,
                            1,
                        )

                    if matched_selector:
                        data["promo_text"] = (data.get("promo_text") or "") or None

                except PlaywrightTimeoutError:
                    if debug_capture_enabled:
                        try:
                            page.screenshot(path=str(DEBUG_DIR / f"{store_name.lower()}_error.png"), full_page=True)
                            (DEBUG_DIR / f"{store_name.lower()}_error.html").write_text(page.content(), encoding="utf-8")
                        except Exception:
                            pass
                    data["promo_text"] = (data.get("promo_text") or "") + " [timeout]"
                except Exception as e:
                    if debug_capture_enabled:
                        try:
                            page.screenshot(path=str(DEBUG_DIR / f"{store_name.lower()}_error.png"), full_page=True)
                            (DEBUG_DIR / f"{store_name.lower()}_error.html").write_text(page.content(), encoding="utf-8")
                        except Exception:
                            pass
                    data["promo_text"] = (data.get("promo_text") or "") + f" [error: {type(e).__name__}]"
                finally:
                    _close_quietly(page)

                results[store_name] = data

            if save_storage_state:
                try:
                    context.storage_state(path=sp)
                except Exception:
                    pass
            _close_quietly(context)

        _close_quietly(browser)

    return results
