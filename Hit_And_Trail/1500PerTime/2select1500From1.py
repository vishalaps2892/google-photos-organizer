from playwright.sync_api import sync_playwright
import time


# ============================================================
# SETTINGS
# ============================================================

TARGET_COUNT = 1500

# Smaller scroll = more overlap and less chance of skipping.
SCROLL_RATIO = 0.40

# Very short retry interval.
LOAD_CHECK_INTERVAL = 0.20

# We don't wait for "full image loading".
# We only wait briefly for DOM media elements to appear.
MAX_DOM_WAIT = 5.0

# Small pause after a successful click.
SELECTION_DELAY = 0.05


# ============================================================
# CONNECT TO EXISTING CHROME
# ============================================================

def connect_to_photos(p):

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

        raise RuntimeError(
            "Google Photos tab not found."
        )

    page.bring_to_front()
    page.wait_for_timeout(500)

    return browser, page


# ============================================================
# FIND MAIN GOOGLE PHOTOS TIMELINE
# ============================================================

def find_timeline(page):

    elements = page.locator(
        "div, c-wiz"
    )

    candidates = []

    for i in range(elements.count()):

        try:

            element = elements.nth(i)

            info = element.evaluate("""
                el => ({
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight,
                    overflowY:
                        getComputedStyle(el).overflowY
                })
            """)

            if (
                info["scrollHeight"] > 100000
                and
                info["overflowY"]
                in ["auto", "scroll", "overlay"]
            ):

                candidates.append(
                    (
                        element,
                        info["scrollHeight"]
                    )
                )

        except Exception:
            pass

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return candidates[0][0]


# ============================================================
# GET ACTUALLY VISIBLE MEDIA
# ============================================================
#
# IMPORTANT:
#
# We ONLY accept:
#
#   <a href="/photo/...">
#
# This excludes Google's duplicate DIV overlay.
#
# We also check the REAL bounding box instead of
# Playwright's is_visible(), because we discovered that
# Google Photos can report off-screen virtualized elements
# as visible.
# ============================================================

def get_visible_media(page):

    locator = page.locator(
        'a[href*="/photo/"][aria-label^="Photo"], '
        'a[href*="/photo/"][aria-label^="Video"]'
    )

    viewport = page.evaluate("""
        () => ({
            width: window.innerWidth,
            height: window.innerHeight
        })
    """)

    viewport_width = viewport["width"]
    viewport_height = viewport["height"]

    result = []

    total = locator.count()

    for i in range(total):

        try:

            element = locator.nth(i)

            box = element.bounding_box()

            if box is None:
                continue

            x = box["x"]
            y = box["y"]
            width = box["width"]
            height = box["height"]

            right = x + width
            bottom = y + height

            # Must physically intersect browser viewport.
            if not (
                right > 0
                and
                bottom > 0
                and
                x < viewport_width
                and
                y < viewport_height
            ):
                continue

            href = element.get_attribute(
                "href"
            )

            label = element.get_attribute(
                "aria-label"
            )

            if not href or not label:
                continue

            result.append({
                "element": element,
                "href": href,
                "label": label,
                "x": x,
                "y": y,
                "width": width,
                "height": height
            })

        except Exception:
            pass

    # Top → bottom, left → right.
    result.sort(
        key=lambda item: (
            item["y"],
            item["x"]
        )
    )

    return result


# ============================================================
# FIND CHECKBOX ASSOCIATED WITH MEDIA
# ============================================================

def find_checkbox(media):

    parent = media

    for _ in range(10):

        try:

            checkbox = parent.locator(
                '[role="checkbox"]'
            ).first

            if checkbox.count() > 0:

                return checkbox

            parent = parent.locator(
                ".."
            )

        except Exception:

            return None

    return None


# ============================================================
# SELECT ONE MEDIA
# ============================================================

def select_one(item):

    try:

        checkbox = find_checkbox(
            item["element"]
        )

        if checkbox is None:

            return False

        # Click only the checkbox belonging to
        # this exact media item.

        checkbox.dispatch_event(
            "click"
        )

        item["element"].page.wait_for_timeout(
            int(
                SELECTION_DELAY * 1000
            )
        )

        # Confirm selection.
        state = checkbox.get_attribute(
            "aria-checked"
        )

        return state == "true"

    except Exception:

        return False


# ============================================================
# PROCESS CURRENT SCREEN
# ============================================================

def process_visible_media(
    page,
    seen,
    selected_count
):

    media = get_visible_media(
        page
    )

    newly_available = []

    for item in media:

        if item["href"] in seen:
            continue

        # Remember immediately.
        #
        # This prevents the same media from being clicked
        # again if Google Photos rearranges/recreates DOM.
        seen.add(
            item["href"]
        )

        newly_available.append(
            item
        )

    for item in newly_available:

        if selected_count >= TARGET_COUNT:

            break

        success = select_one(
            item
        )

        if success:

            selected_count += 1

            print(
                f"✓ "
                f"{selected_count:4d}"
                f"/{TARGET_COUNT}  "
                f"{item['label']}"
            )

        else:

            print(
                f"⚠ Selection failed: "
                f"{item['label']}"
            )

    return selected_count, len(
        newly_available
    )


# ============================================================
# WAIT ONLY FOR DOM MEDIA
# ============================================================
#
# This is intentionally short.
#
# We don't care whether thumbnails/images have finished
# downloading.
#
# We only care whether the actual selectable <a> elements
# have appeared.
# ============================================================

def wait_for_dom_media(
    page,
    seen
):

    start = time.monotonic()

    while (
        time.monotonic() - start
        <
        MAX_DOM_WAIT
    ):

        media = get_visible_media(
            page
        )

        unseen = [
            item
            for item in media
            if item["href"] not in seen
        ]

        if unseen:

            return media

        time.sleep(
            LOAD_CHECK_INTERVAL
        )

    # Don't fail because loading took longer.
    # Just return whatever is currently there.
    return get_visible_media(
        page
    )


# ============================================================
# MAIN
# ============================================================

with sync_playwright() as p:

    browser, page = connect_to_photos(
        p
    )

    print(
        "Connected:",
        page.url
    )

    timeline = find_timeline(
        page
    )

    if timeline is None:

        print(
            "\nERROR: Google Photos timeline "
            "not found."
        )

        raise SystemExit

    # --------------------------------------------------------
    # START EXACTLY WHERE CHROME CURRENTLY IS.
    # --------------------------------------------------------

    starting_position = (
        timeline.evaluate(
            "el => el.scrollTop"
        )
    )

    print(
        "\n================================"
    )

    print(
        "SELECT 1500 MEDIA"
    )

    print(
        "================================"
    )

    print(
        "Starting position:",
        round(
            starting_position,
            1
        )
    )

    print(
        "\nFinding first actually visible media..."
    )

    # --------------------------------------------------------
    # FIRST SCREEN
    # --------------------------------------------------------

    current_media = get_visible_media(
        page
    )

    if not current_media:

        print(
            "\n❌ No actual visible "
            "Photo/Video found."
        )

        print(
            "Position Chrome where photos "
            "are visible and run again."
        )

        raise SystemExit

    print(
        "✓ Visible media:",
        len(current_media)
    )

    print(
        "First media:"
    )

    print(
        current_media[0]["label"]
    )

    print(
        "Position:",
        f"x={current_media[0]['x']:.1f}, "
        f"y={current_media[0]['y']:.1f}"
    )

    # --------------------------------------------------------
    # STATE FOR THIS RUN ONLY
    # --------------------------------------------------------

    seen = set()

    selected_count = 0

    failed_count = 0

    # ========================================================
    # MAIN LOOP
    # ========================================================

    while selected_count < TARGET_COUNT:

        # ----------------------------------------------------
        # PROCESS EVERYTHING CURRENTLY AVAILABLE.
        #
        # NO WAITING FOR FULL IMAGE LOAD.
        # ----------------------------------------------------

        before = selected_count

        selected_count, new_count = (
            process_visible_media(
                page,
                seen,
                selected_count
            )
        )

        # ----------------------------------------------------
        # TARGET REACHED
        # ----------------------------------------------------

        if selected_count >= TARGET_COUNT:

            break

        # ----------------------------------------------------
        # CURRENT TIMELINE POSITION
        # ----------------------------------------------------

        info = timeline.evaluate("""
            el => ({
                scrollTop: el.scrollTop,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight
            })
        """)

        current_position = (
            info["scrollTop"]
        )

        maximum_position = (
            info["scrollHeight"]
            -
            info["clientHeight"]
        )

        # ----------------------------------------------------
        # ADAPTIVE SCROLL
        # ----------------------------------------------------

        movement = max(
            50,
            int(
                info["clientHeight"]
                *
                SCROLL_RATIO
            )
        )

        new_position = min(
            current_position + movement,
            maximum_position
        )

        if new_position <= (
            current_position + 1
        ):

            print(
                "\n================================"
            )

            print(
                "TIMELINE END REACHED"
            )

            print(
                "================================"
            )

            break

        print(
            "\nScrolling:"
        )

        print(
            f"{current_position:.1f}"
            f" → "
            f"{new_position:.1f}"
        )

        # ----------------------------------------------------
        # SCROLL
        # ----------------------------------------------------

        timeline.evaluate(
            """
            (el, position) => {
                el.scrollTop = position;
            }
            """,
            new_position
        )

        # ----------------------------------------------------
        # IMMEDIATE SCAN
        #
        # Do NOT wait before checking.
        #
        # The media might already be present.
        # ----------------------------------------------------

        current_media = get_visible_media(
            page
        )

        unseen_now = [
            item
            for item in current_media
            if item["href"] not in seen
        ]

        if unseen_now:

            print(
                f"✓ Immediately found "
                f"{len(unseen_now)} new media"
            )

        else:

            # ------------------------------------------------
            # Only now do short retries.
            # ------------------------------------------------

            current_media = (
                wait_for_dom_media(
                    page,
                    seen
                )
            )

        # ----------------------------------------------------
        # PROCESS WHATEVER IS AVAILABLE.
        # ----------------------------------------------------

        selected_count, new_count = (
            process_visible_media(
                page,
                seen,
                selected_count
            )
        )

        # ----------------------------------------------------
        # NEVER STOP JUST BECAUSE ZERO NEW MEDIA APPEARED
        # ON ONE SCAN.
        #
        # The next loop will scroll again.
        # ----------------------------------------------------

        if selected_count == before:

            print(
                "  No new selectable media "
                "in this scan; continuing."
            )

    # ========================================================
    # FINAL
    # ========================================================

    ending_position = (
        timeline.evaluate(
            "el => el.scrollTop"
        )
    )

    print(
        "\n\n================================"
    )

    print(
        "BATCH FINISHED"
    )

    print(
        "================================"
    )

    print(
        "Confirmed selected:",
        selected_count,
        "/",
        TARGET_COUNT
    )

    print(
        "Unique media encountered:",
        len(seen)
    )

    print(
        "Starting position:",
        round(
            starting_position,
            1
        )
    )

    print(
        "Ending position:",
        round(
            ending_position,
            1
        )
    )

    print(
        "\nSelections have NOT been cleared."
    )

    print(
        "No album created."
    )

    print(
        "Nothing deleted."
    )

    print(
        "Nothing downloaded."
    )

    print(
        "Nothing shared."
    )

    print(
        "\nYou can manually handle this batch, "
        "move Chrome to the next starting "
        "position, and run the script again."
    )

    input(
        "\nPress ENTER to finish..."
    )