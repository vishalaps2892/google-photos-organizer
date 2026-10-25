from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta


# Current date for this project.
# Today is 15 Aug 2026.
TODAY = datetime(2026, 8, 15)


def get_day_selectors(page):
    elements = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    results = []

    for i in range(elements.count()):
        try:
            label = elements.nth(i).get_attribute(
                "aria-label"
            )

            if label:
                results.append(label)

        except Exception:
            pass

    return results


def is_august_2026(label):
    """
    Decide whether a currently visible day selector
    belongs to August 2026.
    """

    lower = label.lower()

    # Explicit August date.
    if "aug" in lower:
        return True

    # Recent relative labels.
    # Since today is 15 Aug 2026:
    #
    # Today       = Aug 15
    # Yesterday   = Aug 14
    # Weekday     = recent August date
    #
    # We only treat these as August because we're
    # currently testing the August 2026 section.

    relative = [
        "today",
        "yesterday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    for word in relative:
        if lower.endswith(word):
            return True

    return False


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

    selectors = get_day_selectors(page)

    print(
        "\nDay selectors currently loaded:",
        len(selectors)
    )

    august = [
        label
        for label in selectors
        if is_august_2026(label)
    ]

    print(
        "Possible August 2026 selectors:",
        len(august)
    )

    if not august:

        print("\nNo August selectors found.")
        print(
            "Make sure Google Photos is currently around "
            "the August 2026 section."
        )

        input("\nPress ENTER to finish...")
        raise SystemExit

    print("\n================================")
    print("AUGUST SELECTORS")
    print("================================")

    for label in august:
        print(" ", label)

    print("\nSelecting them...")

    selected = []

    for label in august:

        target = page.locator(
            f'[aria-label="{label}"]'
        ).first

        if target.count() == 0:
            print("⚠ Not found:", label)
            continue

        state = target.get_attribute(
            "aria-checked"
        )

        if state == "true":

            print("Already selected:", label)
            selected.append(label)
            continue

        target.dispatch_event("click")

        page.wait_for_timeout(500)

        # Re-find after Google Photos updates the DOM.
        target = page.locator(
            f'[aria-label="{label}"]'
        ).first

        after = target.get_attribute(
            "aria-checked"
        )

        if after == "true":

            print("✓ Selected:", label)
            selected.append(label)

        else:

            print("⚠ Failed:", label)

    print("\n================================")
    print("RESULT")
    print("================================")

    print(
        f"Selected {len(selected)} "
        f"of {len(august)} selectors."
    )

    print("\nSelected:")

    for label in selected:
        print(" ", label)

    print("\n================================")
    print("IMPORTANT")
    print("================================")

    print("Selection has NOT been cleared.")
    print("Photos/videos remain selected.")
    print("No album was created.")
    print("Nothing was deleted.")
    print("Nothing was downloaded.")
    print("Nothing was shared.")

    input(
        "\nPress ENTER after you finish "
        "checking Google Photos manually..."
    )