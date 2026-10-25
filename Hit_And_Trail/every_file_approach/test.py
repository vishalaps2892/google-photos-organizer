from playwright.sync_api import sync_playwright
from datetime import datetime
import re
import time


TARGET_DATE = datetime(2026, 6, 1)


def find_timeline(page):
    """
    Find the large Google Photos timeline scroll container.
    """

    elements = page.locator("div, c-wiz")

    candidates = []

    for i in range(elements.count()):

        try:
            element = elements.nth(i)

            info = element.evaluate("""
                el => ({
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    overflowY: getComputedStyle(el).overflowY
                })
            """)

            if (
                info["scrollHeight"] > 100000
                and info["overflowY"] in
                ["auto", "scroll", "overlay"]
            ):
                candidates.append(
                    (element, info["scrollHeight"])
                )

        except Exception:
            pass

    if not candidates:
        return None

    # Largest scrollable element should be the timeline.
    candidates.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return candidates[0][0]


def get_media_elements(page):
    """
    Return currently loaded individual photo/video elements.

    Google Photos exposes these through aria-labels such as:

        Photo – Landscape – 28 Dec 2026, 11:33:36
        Video – Portrait – 27 Dec 2026, 15:52:48
    """

    elements = page.locator(
        '[aria-label^="Photo"], '
        '[aria-label^="Video"]'
    )

    result = []

    for i in range(elements.count()):

        try:

            element = elements.nth(i)

            if not element.is_visible():
                continue

            label = element.get_attribute(
                "aria-label"
            )

            if not label:
                continue

            # We only want actual media labels,
            # not unrelated elements.
            if not (
                label.startswith("Photo")
                or label.startswith("Video")
            ):
                continue

            href = None

            if element.evaluate(
                "el => el.tagName"
            ) == "A":

                href = element.get_attribute("href")

            result.append(
                {
                    "element": element,
                    "label": label,
                    "href": href,
                }
            )

        except Exception:
            pass

    return result


def extract_date(label):
    """
    Extract date from a Google Photos media aria-label.

    Expected examples:

        Photo – Landscape – 28 Dec 2026, 11:33:36
        Video – Portrait – 27 Dec 2026, 15:52:48
    """

    # Look for:
    # 28 Dec 2026
    # 7 Aug 2026
    # etc.

    match = re.search(
        r'(\d{1,2})\s+'
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        r'\s+(\d{4})',
        label,
        re.IGNORECASE
    )

    if not match:
        return None

    day = int(match.group(1))
    month_text = match.group(2).title()
    year = int(match.group(3))

    try:

        return datetime.strptime(
            f"{day} {month_text} {year}",
            "%d %b %Y"
        )

    except ValueError:

        return None


def media_key(item):
    """
    Create a key so the same media isn't processed twice.
    """

    if item["href"]:
        return "href:" + item["href"]

    return "label:" + item["label"]


def find_checkbox(media):
    """
    Find the individual media selection checkbox.

    We first look inside the media element.

    If Google Photos keeps the checkbox in a nearby
    ancestor, walk upward and search there.
    """

    # Direct descendant.
    checkbox = media.locator(
        '[role="checkbox"]'
    ).first

    if checkbox.count() > 0:
        return checkbox

    # Walk upward through ancestors.
    for level in range(1, 7):

        try:

            ancestor = media.locator(
                ".." * level
            )

            checkbox = ancestor.locator(
                '[role="checkbox"]'
            ).first

            if checkbox.count() > 0:
                return checkbox

        except Exception:
            pass

    return None


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

        print(
            "Google Photos tab not found."
        )

        raise SystemExit

    page.bring_to_front()
    page.wait_for_timeout(1500)

    print(
        "Connected:",
        page.url
    )

    # --------------------------------------------------
    # FIND TIMELINE
    # --------------------------------------------------

    print(
        "\nFinding Google Photos timeline..."
    )

    timeline = find_timeline(page)

    if timeline is None:

        print(
            "Could not find the main timeline."
        )

        raise SystemExit

    info = timeline.evaluate("""
        el => ({
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            scrollTop: el.scrollTop
        })
    """)

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

    # --------------------------------------------------
    # MOVE TO TOP
    # --------------------------------------------------

    print(
        "\nMoving to newest photos..."
    )

    timeline.evaluate(
        "el => el.scrollTop = 0"
    )

    page.wait_for_timeout(2000)

    print(
        "✓ At timeline top."
    )

    # --------------------------------------------------
    # TRACKING
    # --------------------------------------------------

    discovered = set()

    selected = set()

    failed = set()

    reached_june = False

    step = 0

    last_position = -1

    print(
        "\n================================"
    )
    print(
        "SELECTING MEDIA TO JUNE 2026"
    )
    print(
        "================================"
    )

    print(
        "\nSelection will NOT be cleared."
    )

    # --------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------

    while True:

        step += 1

        page.wait_for_timeout(700)

        media_items = get_media_elements(page)

        new_media = []

        oldest_date = None

        for item in media_items:

            key = media_key(item)

            if key in discovered:
                continue

            discovered.add(key)

            date = extract_date(
                item["label"]
            )

            if date is None:
                continue

            if oldest_date is None or date < oldest_date:
                oldest_date = date

            # If before June 2026,
            # don't select it.
            if date < TARGET_DATE:

                reached_june = True
                continue

            new_media.append(
                (item, date, key)
            )

        # ------------------------------------------------
        # SELECT NEW MEDIA
        # ------------------------------------------------

        newly_selected = 0

        for item, date, key in new_media:

            if key in selected:
                continue

            # Re-find the element by its href if possible.
            if item["href"]:

                media = page.locator(
                    f'a[href="{item["href"]}"]'
                ).first

            else:

                media = page.locator(
                    f'[aria-label="{item["label"]}"]'
                ).first

            if media.count() == 0:
                failed.add(key)
                continue

            try:

                checkbox = find_checkbox(
                    media
                )

                if checkbox is None:

                    # Google Photos may create the
                    # selection checkbox after hovering.
                    try:
                        media.hover(
                            timeout=1500
                        )
                    except Exception:
                        pass

                    page.wait_for_timeout(100)

                    checkbox = find_checkbox(
                        media
                    )

                if checkbox is None:

                    failed.add(key)
                    continue

                before = checkbox.get_attribute(
                    "aria-checked"
                )

                # Already selected.
                if before == "true":

                    selected.add(key)
                    continue

                # Use DOM click event rather than normal
                # Playwright click because Google Photos
                # overlays can intercept pointer events.
                checkbox.dispatch_event(
                    "click"
                )

                page.wait_for_timeout(100)

                # Re-find checkbox after DOM update.
                checkbox = find_checkbox(
                    media
                )

                if checkbox is None:

                    failed.add(key)
                    continue

                after = checkbox.get_attribute(
                    "aria-checked"
                )

                if after == "true":

                    selected.add(key)
                    newly_selected += 1

                else:

                    failed.add(key)

            except Exception:

                failed.add(key)

        # ------------------------------------------------
        # CURRENT POSITION
        # ------------------------------------------------

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
            f"Position: {position:9.0f} / {maximum:9.0f} | "
            f"Visible: {len(media_items):3d} | "
            f"New: {len(new_media):3d} | "
            f"Selected: {len(selected):5d} | "
            f"Failed: {len(failed):3d}"
        )

        if oldest_date:

            print(
                "          Oldest visible/new date:",
                oldest_date.date()
            )

        # ------------------------------------------------
        # STOP CONDITION
        # ------------------------------------------------

        if reached_june:

            print(
                "\n✓ June 2026 boundary reached."
            )

            break

        # ------------------------------------------------
        # SCROLL BACKWARD
        # ------------------------------------------------

        if position >= maximum - 5:

            print(
                "\nReached timeline end."
            )

            break

        # Adaptive movement:
        # use roughly 80% of viewport height.
        movement = max(
            300,
            int(
                info["clientHeight"] * 0.8
            )
        )

        new_position = min(
            position + movement,
            maximum
        )

        # Safety check against getting stuck.
        if new_position <= last_position:

            print(
                "\nTimeline stopped moving."
            )

            break

        last_position = position

        timeline.evaluate(
            """
            (el, position) => {
                el.scrollTop = position;
            }
            """,
            new_position
        )

        page.wait_for_timeout(1000)

    # --------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------

    print(
        "\n================================"
    )
    print(
        "SELECTION COMPLETE"
    )
    print(
        "================================"
    )

    print(
        "Unique media discovered:",
        len(discovered)
    )

    print(
        "Successfully selected:",
        len(selected)
    )

    print(
        "Failed to select:",
        len(failed)
    )

    print(
        "\nSelection has NOT been cleared."
    )

    print(
        "All successfully selected photos/videos "
        "remain selected in Google Photos."
    )

    print(
        "\nNo album was created."
    )

    print(
        "Nothing was deleted."
    )

    print(
        "Nothing was downloaded."
    )

    print(
        "Nothing was shared."
    )

    if failed:

        print(
            "\nWARNING:"
        )

        print(
            "Some media could not be selected."
        )

        print(
            "We should investigate those before "
            "using this as the final transfer algorithm."
        )

    input(
        "\nPress ENTER to finish..."
    )