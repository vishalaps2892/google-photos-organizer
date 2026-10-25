from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    print("Connecting to Chrome...")

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

    print("✓ Connected successfully!")

    for context in browser.contexts:
        for page in context.pages:
            print("\n--- Page ---")
            print("Title:", page.title())
            print("URL:", page.url)

    input("\nPress ENTER to finish...")