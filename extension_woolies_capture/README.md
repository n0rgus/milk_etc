# Woolies Capture Extension (MV3)

## Process

1. Start app:
   `uvicorn app.main:app --reload`
2. Open Capture Center:
   `http://127.0.0.1:8000/capture`
3. Choose **WOOLWORTHS**, click **Reset / Start New Capture Run**.
4. Load unpacked extension in Chrome/Edge (`extension_woolies_capture/`).
5. Click extension icon to start.
6. Leave the tab alone; it will step through product URLs and post prices silently.

## Load unpacked extension (Chrome/Edge)

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension_woolies_capture/` folder.

## Notes

- Keep the Woolworths session logged in within that browser profile.
- Ensure delivery/pickup location is set before starting.
- Click extension icon again to stop capture.
