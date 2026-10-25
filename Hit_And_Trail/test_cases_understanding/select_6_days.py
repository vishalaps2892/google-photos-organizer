from playwright.sync_api import sync_playwright


TARGET_DAYS = [
    "Select all photos from Fri, 26 Dec 2025",
    "Select all photos from Thu, 25 Dec 2025",
    "Select all photos from Wed, 24 Dec 2025",
    "Select all photos from Tue, 23 Dec 2025",
    "Select all photos from Mon, 22 Dec 2025",
    "Select all photos from Sun, 21 Dec 2025",
]


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

    print("Connected:", page.url)
    print("\nSelecting six days...\n")

    results = []

    for target_label in TARGET_DAYS:

        target = page.locator(
            f'[aria-label="{target_label}"]'
        ).first

        if target.count() == 0:
            print("NOT FOUND:", target_label)
            results.append((target_label, "NOT FOUND"))
            continue

        before = target.get_attribute("aria-checked")

        print(
            f"{target_label}"
            f"\n  Before: {before}"
        )

        # Trigger Google's own click handler.
        target.dispatch_event("click")

        page.wait_for_timeout(500)

        # Re-locate because Google Photos can rebuild DOM elements.
        target = page.locator(
            f'[aria-label="{target_label}"]'
        ).first

        after = target.get_attribute("aria-checked")

        print(f"  After:  {after}\n")

        results.append((target_label, after))

    print("================================")
    print("RESULT")
    print("================================")

    successful = 0

    for label, state in results:

        if state == "true":
            print("✓", label)
            successful += 1

        else:
            print("⚠", label, "->", state)

    print(
        f"\nSuccessfully selected: "
        f"{successful}/{len(TARGET_DAYS)} days"
    )

    print("\nNo album was created.")
    print("Nothing was deleted.")
    print("Nothing was downloaded.")
    print("Nothing was shared.")

    input("\nPress ENTER to finish...")