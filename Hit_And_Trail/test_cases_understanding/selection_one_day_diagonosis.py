# we successfully selected one day photos but while selecting the next day photos it is not working we need to diagnose why

from playwright.sync_api import sync_playwright


TARGET = "Select all photos from Fri, 26 Dec 2025"


def get_day_selectors(page):
    """Return all currently available day-selection controls."""

    elements = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    results = []

    for i in range(elements.count()):
        try:
            label = elements.nth(i).get_attribute("aria-label")

            if label:
                results.append(label)

        except Exception:
            pass

    return results


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

    # ----------------------------------------
    # BEFORE SELECTION
    # ----------------------------------------

    print("\n================================")
    print("BEFORE SELECTION")
    print("================================")

    before = get_day_selectors(page)

    print("Day selectors found:", len(before))

    for item in before:
        print(" ", item)

    # ----------------------------------------
    # FIND TARGET
    # ----------------------------------------

    target = page.locator(
        f'[aria-label="{TARGET}"]'
    ).first

    print("\nTarget:", TARGET)
    print("Target count:", target.count())

    if target.count() == 0:
        print("Target not currently available.")
        input("Press ENTER to finish...")
        raise SystemExit

    print(
        "Target state before:",
        target.get_attribute("aria-checked")
    )

    # ----------------------------------------
    # SELECT TARGET
    # ----------------------------------------

    print("\nSelecting 26 Dec 2025...")

    target.dispatch_event("click")

    page.wait_for_timeout(2000)

    # ----------------------------------------
    # AFTER SELECTION
    # ----------------------------------------

    print("\n================================")
    print("AFTER SELECTION")
    print("================================")

    after = get_day_selectors(page)

    print("Day selectors found:", len(after))

    for item in after:
        print(" ", item)

    # ----------------------------------------
    # COMPARE
    # ----------------------------------------

    disappeared = [
        item for item in before
        if item not in after
    ]

    appeared = [
        item for item in after
        if item not in before
    ]

    print("\n================================")
    print("CHANGES")
    print("================================")

    print("\nSelectors that disappeared:")

    if disappeared:
        for item in disappeared:
            print(" -", item)
    else:
        print(" None")

    print("\nSelectors that appeared:")

    if appeared:
        for item in appeared:
            print(" +", item)
    else:
        print(" None")

    # ----------------------------------------
    # CHECK TARGET
    # ----------------------------------------

    target_after = page.locator(
        f'[aria-label="{TARGET}"]'
    ).first

    if target_after.count():

        print(
            "\nTarget state after:",
            target_after.get_attribute("aria-checked")
        )

    # ----------------------------------------
    # CLEAN UP
    # ----------------------------------------

    print("\nDeselecting 26 Dec 2025...")

    target_after = page.locator(
        f'[aria-label="{TARGET}"]'
    ).first

    if target_after.count():

        if target_after.get_attribute("aria-checked") == "true":

            target_after.dispatch_event("click")

            page.wait_for_timeout(1500)

            print("✓ 26 Dec 2025 deselected.")

        else:
            print("26 Dec was already unchecked.")

    print("\n================================")
    print("DONE")
    print("================================")

    print("No album created.")
    print("Nothing deleted.")
    print("Nothing downloaded.")
    print("Nothing shared.")

    input("\nPress ENTER to finish...")