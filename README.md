# Grocery PriceWatch (prototype)

## What this is
A small FastAPI web UI that:
- Stores your regular grocery items
- Holds per-store product URLs (ALDI / Coles / Woolworths)
- Scrapes today's price from each per-product page (Playwright)
- Shows a dashboard of latest prices + best store
- Generates a grouped buy list
- Lets you start a "shop session" and tick what you actually bought

## Quick start (Windows / PowerShell)
```powershell
cd grocery_pricewatch
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --reload
```

Open:
http://127.0.0.1:8000

## Notes
- Your Excel list was imported into `seed_items.json` on first run.
- URLs are blank by default. Click an item and paste store URLs to enable scraping.
- Discount % currently requires a "was price" selector; the scraper is wired to accept it, but it’s not configured yet.
- This prototype scrapes synchronously. For large lists, run per-store scrapes.

## Component version tracking
Visible component versions are shown in the web UI navbar and in each extension popup.

Source of truth: `app/versions.py`

Order-of-magnitude buckets:
- `1.x.x` → Core web UI
- `2.x.x` → Backend API
- `3.x.x` → Capture extension
- `4.x.x` → Link helper extension

When changing code in one of these components, increment that component's patch number and keep the others unchanged.
