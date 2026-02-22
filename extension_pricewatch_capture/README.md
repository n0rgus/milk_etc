# PriceWatch Capture Extension (MV3)

## Load unpacked extension (Chrome/Edge)

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension_pricewatch_capture/` folder.

## How to use

1. Start app server:
   `uvicorn app.main:app --reload`
2. Make sure you are logged in to the store sites and location/delivery settings are correct.
3. Click the extension icon to open the popup.
4. Choose mode:
   - Woolworths only
   - Coles only
   - Sequential: Woolworths then Coles
   - Sequential: Coles then Woolworths
5. Confirm backend base URL (`http://127.0.0.1:8000` by default).
6. Click **Start**.
7. Leave the tab alone while the extension navigates through item URLs and posts captures.
8. Click **Stop** at any time to end the run.

## Troubleshooting

- If captures fail, open extension service worker console and inspect warnings.
- If no price is captured, verify the page is a product detail URL and that the store session is logged in.
- If the app endpoint is unreachable, confirm backend URL and FastAPI server status.
