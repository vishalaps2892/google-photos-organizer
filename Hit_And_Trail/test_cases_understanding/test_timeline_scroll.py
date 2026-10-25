# this script is for testing the scrolling through the timeline

from playwright.sync_api import sync_playwright


def get_day_selectors(page):
    elements = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    days = []

    for i in range(elements.count()):
        try:
            label = elements.nth(i).get_attribute("aria-label")

            if label:
                days.append(label)

        except Exception:
            pass

    return days


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

    # Find all scrollable elements.
    scrollable = page.locator(
        "div, c-wiz"
    )

    target = None

    for i in range(scrollable.count()):

        element = scrollable.nth(i)

        try:

            info = element.evaluate("""
                el => ({
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    scrollTop: el.scrollTop,
                    overflowY: getComputedStyle(el).overflowY
                })
            """)

            # We want the huge Google Photos timeline.
            if (
                info["scrollHeight"] > 100000
                and info["overflowY"] in ["auto", "scroll", "overlay"]
            ):
                target = element

                print("\n✓ Main timeline found")
                print("Scroll height:", info["scrollHeight"])
                print("Client height:", info["clientHeight"])
                print("Current position:", info["scrollTop"])

                break

        except Exception:
            pass

    if target is None:

        print("\nCould not find the main timeline.")
        input("Press ENTER to finish...")
        raise SystemExit

    # -----------------------------------------
    # BEFORE SCROLL
    # -----------------------------------------

    print("\n================================")
    print("BEFORE SCROLL")
    print("================================")

    before = get_day_selectors(page)

    for day in before:
        print(day)

    # -----------------------------------------
    # SCROLL
    # -----------------------------------------

    print("\nScrolling timeline down 600 pixels...")

    target.evaluate("""
        el => {
            el.scrollTop = el.scrollTop + 10000;
        }
    """)

    page.wait_for_timeout(2000)

    # -----------------------------------------
    # AFTER SCROLL
    # -----------------------------------------

    info = target.evaluate("""
        el => ({
            scrollTop: el.scrollTop,
            scrollHeight: el.scrollHeight
        })
    """)

    print("\nNew scroll position:", info["scrollTop"])

    print("\n================================")
    print("AFTER SCROLL")
    print("================================")

    after = get_day_selectors(page)

    for day in after:
        print(day)

    # -----------------------------------------
    # COMPARE
    # -----------------------------------------

    disappeared = [
        day for day in before
        if day not in after
    ]

    appeared = [
        day for day in after
        if day not in before
    ]

    print("\n================================")
    print("CHANGES")
    print("================================")

    print("\nDays no longer visible/loaded:")

    for day in disappeared:
        print("-", day)

    if not disappeared:
        print("None")

    print("\nNew days visible/loaded:")

    for day in appeared:
        print("+", day)

    if not appeared:
        print("None")

    print("\nNo photos were selected.")
    print("No album was created.")
    print("Nothing was deleted.")
    print("Nothing was downloaded.")
    print("Nothing was shared.")

    input("\nPress ENTER to finish...")