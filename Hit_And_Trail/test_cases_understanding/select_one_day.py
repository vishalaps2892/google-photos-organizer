from playwright.sync_api import sync_playwright


TARGET = "Select all photos from Fri, 26 Dec 2025"


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
    page.wait_for_timeout(1500)

    target = page.locator(
        f'[aria-label="{TARGET}"]'
    ).first

    print("Connected:", page.url)
    print("Matching selector:", target.count())

    if target.count() == 0:
        print("Target selector not found.")
        input("Press ENTER to finish...")
        raise SystemExit

    print("\nCheckbox before click:")
    print("aria-checked =", target.get_attribute("aria-checked"))

    print("\nTriggering click on the exact Google Photos checkbox...")

    target.dispatch_event("click")

    page.wait_for_timeout(1500)

    # Locate it again because Google Photos can rebuild the DOM.
    target = page.locator(
        f'[aria-label="{TARGET}"]'
    ).first

    print("\nCheckbox after click:")
    print("aria-checked =", target.get_attribute("aria-checked"))

    if target.get_attribute("aria-checked") == "true":
        print("\n✓ 26 Dec 2025 is selected.")
    else:
        print("\n⚠ Selection did not change.")

    print("\nNo album was created.")
    print("Nothing was deleted.")
    print("Nothing was shared.")

    input("\nPress ENTER to finish...")