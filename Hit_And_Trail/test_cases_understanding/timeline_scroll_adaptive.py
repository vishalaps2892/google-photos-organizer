# thi script will 
'''It will:
Find the real Google Photos timeline automatically.
Read the currently visible dates.
Scroll based on the timeline's actual viewport size, not a fixed 10,000 pixels.
Wait for Google Photos to load.
Record every new date it encounters.
Continue until we reach January 2025.
Show progress as it goes.'''

from playwright.sync_api import sync_playwright
import re
import time


YEAR = 2025


def get_day_selectors(page):
    """Get all currently loaded Google Photos day selectors."""

    elements = page.locator(
        '[aria-label^="Select all photos from"]'
    )

    days = set()

    for i in range(elements.count()):
        try:
            label = elements.nth(i).get_attribute("aria-label")

            if label:
                days.add(label)

        except Exception:
            pass

    return days


def extract_dates(labels):
    """Extract YYYY-MM-DD from Google Photos day labels."""

    month_map = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    dates = set()

    pattern = re.compile(
        r"Select all photos from "
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), "
        r"(\d{1,2}) "
        r"([A-Za-z]{3}) "
        r"(\d{4})"
    )

    for label in labels:

        match = pattern.search(label)

        if not match:
            continue

        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))

        if year != YEAR:
            continue

        month = month_map.get(month_name)

        if month:
            dates.add(
                (year, month, day)
            )

    return dates


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

    # ----------------------------------------
    # FIND MAIN TIMELINE
    # ----------------------------------------

    print("\nFinding Google Photos timeline...")

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

                print("✓ Timeline found")
                print(
                    "  Scroll height:",
                    info["scrollHeight"]
                )
                print(
                    "  Viewport height:",
                    info["clientHeight"]
                )
                print(
                    "  Current position:",
                    info["scrollTop"]
                )

                break

        except Exception:
            pass

    if timeline is None:
        print("Could not find main timeline.")
        raise SystemExit

    # ----------------------------------------
    # SCANNING
    # ----------------------------------------

    discovered = set()

    print("\n================================")
    print(f"SCANNING {YEAR}")
    print("================================")
    print("\nRead-only scan started.\n")

    previous_count = 0
    no_change_count = 0

    for step in range(200):

        # Read currently loaded day selectors.
        labels = get_day_selectors(page)

        dates = extract_dates(labels)

        before = len(discovered)

        discovered.update(dates)

        new_count = len(discovered) - before

        if new_count:
            no_change_count = 0
        else:
            no_change_count += 1

        # Sort newest first.
        sorted_dates = sorted(
            discovered,
            reverse=True
        )

        print(
            f"Step {step + 1:3d} | "
            f"Visible days: {len(dates):2d} | "
            f"Discovered: {len(discovered):3d} | "
            f"New: {new_count:2d}"
        )

        if sorted_dates:

            newest = sorted_dates[0]
            oldest = sorted_dates[-1]

            print(
                f"           "
                f"Range: "
                f"{newest[0]:04d}-{newest[1]:02d}-{newest[2]:02d}"
                f" → "
                f"{oldest[0]:04d}-{oldest[1]:02d}-{oldest[2]:02d}"
            )

        # ------------------------------------
        # CHECK WHETHER WE REACHED JANUARY
        # ------------------------------------

        reached_january = any(
            year == YEAR and month == 1
            for year, month, day in discovered
        )

        if reached_january:

            print(
                "\n✓ January 2025 reached."
            )

            break

        # ------------------------------------
        # ADAPTIVE SCROLL
        # ------------------------------------

        info = timeline.evaluate("""
            el => ({
                scrollTop: el.scrollTop,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight
            })
        """)

        current_position = info["scrollTop"]
        max_position = (
            info["scrollHeight"]
            - info["clientHeight"]
        )

        # Use the actual viewport height.
        viewport = info["clientHeight"]

        # Start with about 8 viewport heights.
        scroll_amount = viewport * 8

        # Never scroll beyond the timeline.
        new_position = min(
            current_position + scroll_amount,
            max_position
        )

        if new_position == current_position:

            print("\nReached bottom of timeline.")
            break

        timeline.evaluate(
            """
            (el, position) => {
                el.scrollTop = position;
            }
            """,
            new_position
        )

        # Give Google Photos time to load.
        page.wait_for_timeout(1800)

    # ----------------------------------------
    # RESULTS
    # ----------------------------------------

    print("\n================================")
    print("SCAN COMPLETE")
    print("================================")

    sorted_dates = sorted(
        discovered,
        reverse=True
    )

    print(
        f"\nUnique {YEAR} days discovered:",
        len(sorted_dates)
    )

    if sorted_dates:

        print("\nDates found:")

        for year, month, day in sorted_dates:

            print(
                f"{year:04d}-{month:02d}-{day:02d}"
            )

    print("\nNothing was selected.")
    print("No album was created.")
    print("Nothing was deleted.")
    print("Nothing was downloaded.")
    print("Nothing was shared.")

    input("\nPress ENTER to finish...")