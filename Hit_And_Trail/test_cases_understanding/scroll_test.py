# this script is for finding the text while scrolling the page and print the text if found

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(
        "http://127.0.0.1:9222"
    )

    page = None

    for context in browser.contexts:
        for candidate in context.pages:
            if "photos.google.com" in candidate.url:
                page = candidate
                break
        if page:
            break

    if page is None:
        print("Google Photos tab not found.")
        raise SystemExit

    page.bring_to_front()

    print("Connected to:", page.url)
    print("Starting timeline inspection...\n")

    # Give Google Photos time to finish loading.
    page.wait_for_timeout(3000)

    found = False

    for step in range(1, 11):
        print(f"Scroll {step}/10")

        # Scroll down approximately one screen.
        page.mouse.wheel(0, 900)

        # Give Google Photos time to load more media.
        page.wait_for_timeout(1500)

        text = page.locator("body").inner_text()

        if "2025" in text:
            print("\n✓ 2025 FOUND!")
            found = True

            for line in text.splitlines():
                if "2025" in line:
                    print("   ", repr(line))

            break

    if not found:
        print("\n2025 was not found after 10 scrolls.")

    print("\nTest complete.")
    input("Press ENTER to finish...")