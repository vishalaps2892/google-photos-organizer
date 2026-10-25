from playwright.sync_api import sync_playwright
import re


YEAR = 2025


def get_day_labels(page):
    elements = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    labels = set()

    for i in range(elements.count()):
        try:
            label = elements.nth(i).get_attribute("aria-label")

            if label:
                labels.add(label)

        except Exception:
            pass

    return labels


def get_years(labels):
    years = set()

    pattern = re.compile(r"(\d{4})")

    for label in labels:

        match = pattern.search(label)

        if match:
            years.add(int(match.group(1)))

    return years


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

    # ----------------------------------------
    # FIND MAIN TIMELINE
    # ----------------------------------------

    scrollable = page.locator("div, c-wiz")

    timeline = None

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

            if (
                info["scrollHeight"] > 100000
                and info["overflowY"] in
                ["auto", "scroll", "overlay"]
            ):

                timeline = element
                break

        except Exception:
            pass

    if timeline is None:
        print("Main timeline not found.")
        raise SystemExit

    # ----------------------------------------
    # START AT TOP
    # ----------------------------------------

    timeline.evaluate("""
        el => {
            el.scrollTop = 0;
        }
    """)

    page.wait_for_timeout(2500)

    print("================================")
    print("FINDING 2025")
    print("================================")

    print("\nScanning entire timeline.")
    print("No fixed step limit.\n")

    # ----------------------------------------
    # SCAN ENTIRE TIMELINE
    # ----------------------------------------

    step = 0
    last_position = -1

    while True:

        step += 1

        labels = get_day_labels(page)
        years = get_years(labels)

        info = timeline.evaluate("""
            el => ({
                scrollTop: el.scrollTop,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight
            })
        """)

        position = info["scrollTop"]
        maximum = (
            info["scrollHeight"]
            - info["clientHeight"]
        )

        print(
            f"Step {step:3d} | "
            f"Position: {position:10.0f} / "
            f"{maximum:10.0f} | "
            f"Selectors: {len(labels):2d} | "
            f"Years: {sorted(years)}"
        )

        # ------------------------------------
        # FOUND 2025
        # ------------------------------------

        if YEAR in years:

            print("\n✓ 2025 FOUND!")

            print("\nVisible 2025 selectors:")

            for label in sorted(labels):
                print(" ", label)

            print(
                "\nTimeline position:",
                position
            )

            break

        # ------------------------------------
        # REACHED BOTTOM
        # ------------------------------------

        if position >= maximum - 5:

            print(
                "\nReached bottom of timeline."
            )

            print(
                "2025 was not found."
            )

            break

        # ------------------------------------
        # PREVENT STUCK LOOP
        # ------------------------------------

        if position <= last_position:

            print(
                "\nTimeline stopped moving."
            )

            # Try a browser-style scroll.
            page.mouse.wheel(
                0,
                info["clientHeight"]
            )

            page.wait_for_timeout(1000)

            # Read position again.
            new_position = timeline.evaluate(
                "el => el.scrollTop"
            )

            if new_position <= position:

                print(
                    "Could not move further."
                )

                break

        last_position = position

        # ------------------------------------
        # ADAPTIVE SCROLL
        # ------------------------------------

        viewport = info["clientHeight"]

        # One viewport at a time.
        movement = viewport

        new_position = min(
            position + movement,
            maximum
        )

        timeline.evaluate(
            """
            (el, position) => {
                el.scrollTop = position;
            }
            """,
            new_position
        )

        # Wait for Google Photos to render.
        page.wait_for_timeout(1500)

    print("\n================================")
    print("DONE")
    print("================================")

    print("\nRead-only test.")
    print("Nothing was selected.")
    print("No album was created.")
    print("Nothing was deleted.")
    print("Nothing was downloaded.")
    print("Nothing was shared.")

    input("\nPress ENTER to finish...")