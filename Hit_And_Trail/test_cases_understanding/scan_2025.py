from playwright.sync_api import sync_playwright
from collections import Counter
import re
import time


MEDIA_PATTERN = re.compile(
    r"^(Photo|Video)\s+–\s+.*?\s+–\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4}),"
)


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

    print("Connected:", page.url)

    # Let Google Photos settle.
    page.wait_for_timeout(3000)

    media = set()

    print("\nScanning Google Photos...")
    print("This is READ ONLY. Nothing will be changed.\n")

    # We will make a maximum of 150 scrolls for this test.
    for step in range(150):

        # Find all elements whose aria-label starts with Photo or Video.
        elements = page.locator(
            '[aria-label^="Photo –"], [aria-label^="Video –"]'
        )

        current_count = elements.count()

        before = len(media)

        for i in range(current_count):
            try:
                label = elements.nth(i).get_attribute("aria-label")

                if label:
                    media.add(label)

            except Exception:
                pass

        new_items = len(media) - before

        print(
            f"Scroll {step + 1:3d} | "
            f"visible media: {current_count:4d} | "
            f"unique discovered: {len(media):5d} | "
            f"new: {new_items:3d}"
        )

        # Extract all years currently discovered.
        years = []

        for label in media:
            match = MEDIA_PATTERN.match(label)

            if match:
                year = int(match.group(4))
                years.append(year)

        # Once we've gone past 2025 into 2024, stop.
        if years and max(years) < 2025:
            print("\nReached dates before 2025.")
            break

        # Scroll down.
        page.mouse.wheel(0, 1200)

        # Give Google Photos time to load.
        page.wait_for_timeout(1000)

    # -----------------------------
    # Results
    # -----------------------------

    print("\n================================")
    print("SCAN RESULTS")
    print("================================")

    year_counter = Counter()
    type_counter = Counter()

    for label in media:

        match = MEDIA_PATTERN.match(label)

        if not match:
            continue

        media_type = match.group(1)
        year = int(match.group(4))

        year_counter[year] += 1
        type_counter[media_type] += 1

    print("\nBy year:")

    for year in sorted(year_counter, reverse=True):
        print(f"{year}: {year_counter[year]}")

    print("\nBy media type:")

    for media_type, count in type_counter.items():
        print(f"{media_type}: {count}")

    print("\nTotal unique media discovered:", len(media))

    print("\nFirst 20 discovered items:")

    for label in sorted(media)[:20]:
        print(label)

    input("\nPress ENTER to finish...")