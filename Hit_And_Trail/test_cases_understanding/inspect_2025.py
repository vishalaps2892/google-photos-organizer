# this script is for inspecting the page for the text "2025" only 99 attributes

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

    print("Connected:", page.url)

    # Scroll until 2025 is visible.
    print("\nSearching for 2025...")

    found = False

    for step in range(20):
        text = page.locator("body").inner_text()

        if "2025" in text:
            print(f"✓ 2025 found after {step} scrolls")
            found = True
            break

        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1000)

    if not found:
        print("2025 not found.")
        input("Press ENTER to finish...")
        raise SystemExit

    print("\n--- Inspecting visible elements ---")

    # Get elements that have aria-label attributes.
    elements = page.locator("[aria-label]")
    count = elements.count()

    print("Elements with aria-label:", count)

    shown = 0

    for i in range(count):
        element = elements.nth(i)

        try:
            label = element.get_attribute("aria-label")

            if label:
                print(
                    f"{shown}: "
                    f"tag={element.evaluate('(e) => e.tagName')} "
                    f"aria-label={label!r}"
                )

                shown += 1

                if shown >= 100:
                    break

        except Exception:
            pass

    print("\n--- Images currently loaded ---")

    images = page.locator("img")

    print("Image elements:", images.count())

    for i in range(min(images.count(), 50)):
        img = images.nth(i)

        try:
            print(
                i,
                "alt=", repr(img.get_attribute("alt")),
                "aria-label=", repr(img.get_attribute("aria-label"))
            )
        except Exception:
            pass

    print("\nInspection complete.")
    input("Press ENTER to finish...")