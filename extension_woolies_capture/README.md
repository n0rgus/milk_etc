# Woolies Capture Extension (MV3)

## Load unpacked extension (Chrome/Edge)

1. Open `chrome://extensions` (Chrome) or `edge://extensions` (Edge).
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension_woolies_capture/` folder from this repo.

## Start the FastAPI app

Run your app locally so extension requests can reach:
- `http://127.0.0.1:8000/api/next?store=WOOLWORTHS`
- `http://127.0.0.1:8000/api/capture`

## Run capture loop

1. In the browser, open any tab (the extension will reuse the currently active tab).
2. Click the extension icon to **start** capture.
3. Click the extension icon again at any time to **stop** capture.

## Woolworths session requirements

- Stay logged into Woolworths in that same browser profile if login is required.
- Confirm your delivery/pickup location is set correctly before starting.
- Keep the active capture tab focused while it navigates between product pages.
