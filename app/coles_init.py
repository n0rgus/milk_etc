from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def init_coles_session(url: str, state_path: str, slowmo_ms: int = 250) -> None:
    target_url = (url or "").strip()
    if not target_url:
        raise ValueError("A Coles URL is required")

    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False, slow_mo=max(0, int(slowmo_ms or 0)))
        context = browser.new_context()
        page = context.new_page()
        page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

        # Human-in-the-loop: user completes any challenge in a visible browser window.
        page.pause()

        context.storage_state(path=str(path))
        context.close()
        browser.close()
