import subprocess
import time
from playwright.sync_api import sync_playwright

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeDebug"
DEBUG_PORT = 9222


with sync_playwright() as p:

    # Start Chrome with remote debugging enabled
    chrome = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ])

    print(f"Chrome started on port {DEBUG_PORT}")

    # Give Chrome a moment to start
    time.sleep(2)

    # Connect Playwright to the Chrome we just started
    browser = p.chromium.connect_over_cdp(
        f"http://127.0.0.1:{DEBUG_PORT}"
    )

    print("Connected to Chrome successfully!")

    # Get Chrome context
    context = browser.contexts[0]

    # Get existing tabs
    pages = context.pages

    print(f"Open tabs: {len(pages)}")

    if pages:
        page = pages[0]
    else:
        page = context.new_page()

    # Open Google Photos
    page.goto("https://photos.google.com")

    print("Google Photos opened.")
    print("URL:", page.url)

    input("Press Enter to close...")
    
    browser.close()
    chrome.terminate()