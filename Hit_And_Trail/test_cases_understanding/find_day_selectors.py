#  this script try to find the the button on top for select whole day as one

from playwright.sync_api import sync_playwright


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
    page.wait_for_timeout(2000)

    selectors = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    print("Day selectors currently loaded:", selectors.count())
    print()

    for i in range(selectors.count()):
        try:
            label = selectors.nth(i).get_attribute("aria-label")
            print(i, label)
        except Exception:
            pass

    print("\nNo photos were selected.")
    print("No albums were created.")
    print("This was read-only.")

    input("\nPress ENTER to finish...")