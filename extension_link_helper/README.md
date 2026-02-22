# PriceWatch Link Helper (MV3)

This extension helps link an item in the PriceWatch web app to equivalent product pages on:
- Woolworths
- Coles
- Aldi

## How it works
1. Open an item edit page in the app: `http://127.0.0.1:8000/items/<id>`
2. Ensure the product name is in the input with id `name`
3. Click the extension icon and choose:
   - Open searches for all three stores, or just one
4. In each store tab, click the correct search result
5. When you land on a product page, the extension captures:
   - URL
   - product label (best-effort)
   and fills the corresponding URL/label fields in the original edit form.

## Form field matching
The extension attempts to find inputs by heuristics:
- URL input: id/name contains both store name and "url" (e.g. `coles_url`, `woolworths_url`, `aldi_url`)
- Label input: id/name contains store name and "label" (or "title")

If it can't find the URL field, it will alert the captured URL so you can paste manually.

## Install (Chrome/Edge)
Load unpacked extension:
1. Open `chrome://extensions` (or `edge://extensions`)
2. Enable Developer mode
3. "Load unpacked" → select the `extension_link_helper/` folder

Quick note (so Codex doesn’t miss it)

This extension will work best if your edit form has predictable fields like:

coles_url, coles_label

woolworths_url, woolworths_label

aldi_url, aldi_label

If your current form uses different names, the heuristic may still find them, but if you paste me one example of the relevant HTML inputs I can tighten the selectors for near-100% reliability.
