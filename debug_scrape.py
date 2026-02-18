import argparse
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DEFAULT_SELECTORS = {
    "WOOLWORTHS": 'div.product-price_component_price-lead__vlm8f',
    "COLES": 'span.price__value[data-testid="pricing"]',
    "ALDI": "span.base-price__regular span",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True, choices=["ALDI", "COLES", "WOOLWORTHS"])
    ap.add_argument("--url", required=True)
    ap.add_argument("--selector", default=None)
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--slowmo", type=int, default=250)  # ms
    ap.add_argument("--timeout", type=int, default=45000)
    ap.add_argument("--pause", action="store_true", help="pause with Playwright inspector")
    ap.add_argument("--out", default="debug_out", help="folder for screenshots/html")
    args = ap.parse_args()

    selector = args.selector or DEFAULT_SELECTORS[args.store]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful,
            slow_mo=args.slowmo if args.headful else 0,
        )
        context = browser.new_context()
        page = context.new_page()

        print(f"[+] goto: {args.url}")
        page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)

        # Optional: wait a bit for JS-heavy sites
        page.wait_for_timeout(2000)

        print(f"[+] wait_for_selector: {selector}")
        try:
            page.wait_for_selector(selector, timeout=20000)
        except Exception as e:
            print(f"[!] selector not found: {e}")

        loc = page.locator(selector).first
        count = page.locator(selector).count()
        print(f"[+] matched count = {count}")

        if count > 0:
            # Highlight the element
            loc.evaluate(
                """(el) => {
                    el.scrollIntoView({behavior:'instant', block:'center'});
                    el.style.outline = '4px solid magenta';
                    el.style.background = 'rgba(255,0,255,0.08)';
                }"""
            )
            text = loc.inner_text().strip()
            print(f"[+] inner_text: {text}")
        else:
            text = None

        # Save artifacts
        safe_store = args.store.lower()
        page.screenshot(path=str(out_dir / f"{safe_store}.png"), full_page=True)
        html = page.content()
        (out_dir / f"{safe_store}.html").write_text(html, encoding="utf-8")
        print(f"[+] wrote {out_dir}/{safe_store}.png and .html")

        if args.pause:
            # Opens Playwright Inspector (lets you test selectors live)
            page.pause()
        elif args.headful:
            # Keep the browser open briefly so you can eyeball it
            print("[i] keeping browser open for 10 seconds...")
            time.sleep(10)

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
