from playwright.sync_api import sync_playwright
import time



# ============================================================
# SETTINGS
# ============================================================

def get_target_count():
    while True:
        value = input("Enter the number of media to select (1-20000): ")

        # 1. Check if the input is a valid whole number
        try:
            target_count = int(value)
        except ValueError:
            print("Invalid input. Please enter a number using digits only.")
            continue

        # 2. Check if the number is within the range (1 to 20,000)
        if not (1 <= target_count <= 20000):
            print("Number out of range! Please enter a value between 1 and 20,000.")
            continue

        # Valid input reached
        return target_count


TARGET_COUNT = get_target_count()



# Move 40% of viewport each time.
# This gives us overlap and reduces skipped media.
SCROLL_RATIO = 0.40

# Very short DOM retry interval.
LOAD_CHECK_INTERVAL = 0.20

# We don't wait for images to fully load.
MAX_DOM_WAIT = 5.0

# After a group of clicks, give Google Photos a tiny amount
# of time to update aria-checked.
VERIFY_DELAY = 0.10


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

    return browser, page


# ============================================================
# FIND MAIN TIMELINE
# ============================================================

def find_timeline(page):

    print("Finding Google Photos timeline...")

    # Find the largest genuinely scrollable element.
    # We don't rely on overflowY because Google Photos
    # can report it differently depending on the UI state.

    result = page.evaluate("""
        () => {

            const elements =
                document.querySelectorAll(
                    'body *'
                );

            let best = null;
            let bestDistance = 0;

            for (const el of elements) {

                try {

                    const scrollHeight =
                        el.scrollHeight;

                    const clientHeight =
                        el.clientHeight;

                    const distance =
                        scrollHeight -
                        clientHeight;

                    // Ignore tiny containers.
                    if (
                        clientHeight < 300 ||
                        scrollHeight < 50000 ||
                        distance < 20000
                    ) {
                        continue;
                    }

                    if (
                        distance > bestDistance
                    ) {

                        best = el;
                        bestDistance =
                            distance;
                    }

                } catch (e) {
                    // Ignore inaccessible elements.
                }
            }

            if (!best) {
                return null;
            }

            // Give it a temporary unique marker so
            // Playwright can retrieve the exact element.
            best.setAttribute(
                "data-chatgpt-timeline",
                "true"
            );

            return {
                scrollHeight:
                    best.scrollHeight,

                clientHeight:
                    best.clientHeight,

                scrollTop:
                    best.scrollTop,

                distance:
                    best.scrollHeight -
                    best.clientHeight,

                tag:
                    best.tagName,

                className:
                    best.className?.toString()
                    || ""
            };
        }
    """)

    if result is None:

        print(
            "❌ Could not find a large scrollable "
            "timeline container."
        )

        return None

    print(
        "✓ Timeline found"
    )

    print(
        "  Tag:",
        result["tag"]
    )

    print(
        "  Scroll height:",
        result["scrollHeight"]
    )

    print(
        "  Viewport:",
        result["clientHeight"]
    )

    print(
        "  Current position:",
        result["scrollTop"]
    )

    print(
        "  Scrollable distance:",
        result["distance"]
    )

    timeline = page.locator(
        '[data-chatgpt-timeline="true"]'
    ).first

    if timeline.count() == 0:

        print(
            "❌ Timeline marker could not be retrieved."
        )

        return None

    return timeline

# ============================================================
# GET VISIBLE MEDIA
# ============================================================
#
# EVERYTHING HERE RUNS INSIDE THE BROWSER.
#
# This is much faster than calling bounding_box() for every
# media through Playwright.
# ============================================================

def get_visible_media(page):

    return page.evaluate("""
        () => {

            const vw =
                window.innerWidth;

            const vh =
                window.innerHeight;

            const elements =
                document.querySelectorAll(
                    'a[href*="/photo/"][aria-label^="Photo"],' +
                    'a[href*="/photo/"][aria-label^="Video"]'
                );

            const result = [];

            for (const el of elements) {

                const rect =
                    el.getBoundingClientRect();

                const right =
                    rect.left + rect.width;

                const bottom =
                    rect.top + rect.height;

                // Actual physical viewport intersection.
                if (
                    right <= 0 ||
                    bottom <= 0 ||
                    rect.left >= vw ||
                    rect.top >= vh
                ) {
                    continue;
                }

                const href =
                    el.getAttribute("href");

                const label =
                    el.getAttribute("aria-label");

                if (!href || !label) {
                    continue;
                }

                result.push({
                    href: href,
                    label: label,
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height
                });
            }

            // Top -> bottom
            // Left -> right
            result.sort(
                (a, b) => {

                    if (
                        Math.abs(
                            a.y - b.y
                        ) > 30
                    ) {
                        return a.y - b.y;
                    }

                    return a.x - b.x;
                }
            );

            return result;
        }
    """)


# ============================================================
# FAST SELECT VISIBLE MEDIA
# ============================================================
#
# This is the major speed improvement.
#
# Detection + checkbox lookup + click happen inside ONE
# browser-side JavaScript call.
#
# No Python <-> Chrome round trip for every photo.
# ============================================================

def fast_select_visible(
    page,
    seen,
    remaining
):

    result = page.evaluate(
        """
        ({seenArray, remaining}) => {

            const seen =
                new Set(seenArray);

            const vw =
                window.innerWidth;

            const vh =
                window.innerHeight;

            const elements =
                document.querySelectorAll(
                    'a[href*="/photo/"][aria-label^="Photo"],' +
                    'a[href*="/photo/"][aria-label^="Video"]'
                );

            const candidates = [];

            for (const el of elements) {

                const rect =
                    el.getBoundingClientRect();

                const right =
                    rect.left + rect.width;

                const bottom =
                    rect.top + rect.height;

                if (
                    right <= 0 ||
                    bottom <= 0 ||
                    rect.left >= vw ||
                    rect.top >= vh
                ) {
                    continue;
                }

                const href =
                    el.getAttribute("href");

                const label =
                    el.getAttribute("aria-label");

                if (!href || !label) {
                    continue;
                }

                if (seen.has(href)) {
                    continue;
                }

                candidates.push({
                    el: el,
                    href: href,
                    label: label,
                    x: rect.left,
                    y: rect.top
                });
            }

            // Top -> bottom, left -> right.
            candidates.sort(
                (a, b) => {

                    if (
                        Math.abs(
                            a.y - b.y
                        ) > 30
                    ) {
                        return a.y - b.y;
                    }

                    return a.x - b.x;
                }
            );

            const selected = [];

            for (const item of candidates) {

                if (
                    selected.length >= remaining
                ) {
                    break;
                }

                // --------------------------------------------
                // Find the checkbox in the surrounding
                // Google Photos container.
                // --------------------------------------------

                let container =
                    item.el;

                let checkbox = null;

                for (
                    let level = 0;
                    level < 10 && container;
                    level++
                ) {

                    checkbox =
                        container.querySelector(
                            '[role="checkbox"]'
                        );

                    if (checkbox) {
                        break;
                    }

                    container =
                        container.parentElement;
                }

                if (!checkbox) {
                    continue;
                }

                // --------------------------------------------
                // IMPORTANT:
                //
                // If already checked, DON'T click it.
                //
                // This prevents accidental toggling if a
                // previous selection was not manually cleared.
                // --------------------------------------------

                const state =
                    checkbox.getAttribute(
                        "aria-checked"
                    );

                if (state === "true") {

                    selected.push({
                        href: item.href,
                        label: item.label,
                        alreadySelected: true
                    });

                    continue;
                }

                // --------------------------------------------
                // DIRECT DOM CLICK
                //
                // No Playwright round trip.
                // No artificial delay.
                // --------------------------------------------

                checkbox.click();

                selected.push({
                    href: item.href,
                    label: item.label,
                    alreadySelected: false
                });
            }

            return selected;
        }
        """,
        {
            "seenArray": list(seen),
            "remaining": remaining
        }
    )

    return result


# ============================================================
# CHECK WHETHER NEW MEDIA HAS APPEARED
# ============================================================

def has_unseen_media(
    page,
    seen
):

    media = get_visible_media(
        page
    )

    for item in media:

        if item["href"] not in seen:

            return True

    return False


# ============================================================
# WAIT ONLY FOR DOM APPEARANCE
# ============================================================

def wait_for_dom(
    page,
    seen
):

    start = time.monotonic()

    while (
        time.monotonic() - start
        <
        MAX_DOM_WAIT
    ):

        if has_unseen_media(
            page,
            seen
        ):

            return True

        time.sleep(
            LOAD_CHECK_INTERVAL
        )

    return False


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
            "\nERROR: Timeline not found."
        )

        raise SystemExit

    # --------------------------------------------------------
    # START EXACTLY WHERE CHROME CURRENTLY IS.
    # --------------------------------------------------------

    start_position = timeline.evaluate(
        "el => el.scrollTop"
    )

    print(
        "\n================================"
    )

    print(
        "FAST 1500 MEDIA SELECTOR"
    )

    print(
        "================================"
    )

    print(
        "Starting position:",
        round(
            start_position,
            1
        )
    )

    # --------------------------------------------------------
    # FIND STARTING MEDIA
    # --------------------------------------------------------

    visible = get_visible_media(
        page
    )

    if not visible:

        print(
            "\n❌ No actual visible media found."
        )

        raise SystemExit

    print(
        "\n✓ Starting media:"
    )

    print(
        visible[0]["label"]
    )

    print(
        "Position:",
        f"x={visible[0]['x']:.1f}, "
        f"y={visible[0]['y']:.1f}"
    )

    print(
        "\nSelecting..."
    )

    # --------------------------------------------------------
    # STATE ONLY FOR THIS RUN
    # --------------------------------------------------------

    seen = set()

    selected_count = 0

    skipped_already_selected = 0

    failed_count = 0

    first_selected = None

    last_selected = None

    # ========================================================
    # MAIN LOOP
    # ========================================================

    while selected_count < TARGET_COUNT:

        # ----------------------------------------------------
        # FAST SELECT CURRENT SCREEN
        # ----------------------------------------------------

        remaining = (
            TARGET_COUNT
            -
            selected_count
        )

        selected_items = (
            fast_select_visible(
                page,
                seen,
                remaining
            )
        )

        # ----------------------------------------------------
        # PROCESS RESULTS
        # ----------------------------------------------------

        for item in selected_items:

            href = item["href"]

            if href in seen:
                continue

            seen.add(
                href
            )

            if item["alreadySelected"]:

                skipped_already_selected += 1

                # Since it is already selected, count it as
                # part of the current batch rather than
                # clicking it and toggling it off.
                selected_count += 1

                print(
                    f"✓ "
                    f"{selected_count:4d}"
                    f"/{TARGET_COUNT}  "
                    f"{item['label']}"
                    f" [already selected]"
                )

            else:

                selected_count += 1

                if first_selected is None:

                    first_selected = (
                        item["label"]
                    )

                last_selected = (
                    item["label"]
                )

                print(
                    f"✓ "
                    f"{selected_count:4d}"
                    f"/{TARGET_COUNT}  "
                    f"{item['label']}"
                )

            if (
                selected_count
                >=
                TARGET_COUNT
            ):

                break

        # ----------------------------------------------------
        # TARGET REACHED
        # ----------------------------------------------------

        if selected_count >= TARGET_COUNT:

            break

        # ----------------------------------------------------
        # TIMELINE POSITION
        # ----------------------------------------------------

        info = timeline.evaluate("""
            el => ({
                scrollTop:
                    el.scrollTop,

                scrollHeight:
                    el.scrollHeight,

                clientHeight:
                    el.clientHeight
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
        # SCROLL
        # ----------------------------------------------------

        movement = max(
            200,
            int(
                info["clientHeight"]
                *
                SCROLL_RATIO
            )
        )

        new_position = min(
            current_position
            +
            movement,
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
            f"\nScroll "
            f"{current_position:.0f}"
            f" → "
            f"{new_position:.0f}"
        )

        timeline.evaluate(
            """
            (el, pos) => {
                el.scrollTop = pos;
            }
            """,
            new_position
        )

        # ----------------------------------------------------
        # IMMEDIATE SCAN
        #
        # No artificial sleep here.
        # If Google Photos has already inserted the media,
        # we select it immediately.
        # ----------------------------------------------------

        time.sleep(
            0.05
        )

        if not has_unseen_media(
            page,
            seen
        ):

            # Only wait if genuinely nothing new exists.
            print(
                "Waiting for DOM media..."
            )

            wait_for_dom(
                page,
                seen
            )

        # ----------------------------------------------------
        # LOOP BACK AND SELECT
        # ----------------------------------------------------

    # ========================================================
    # FINAL RESULT
    # ========================================================

    end_position = timeline.evaluate(
        "el => el.scrollTop"
    )

    print(
        "\n\n================================"
    )

    print(
        "BATCH COMPLETE"
    )

    print(
        "================================"
    )

    print(
        "Selected:",
        selected_count,
        "/",
        TARGET_COUNT
    )

    print(
        "Unique media encountered:",
        len(seen)
    )

    print(
        "Already-selected encountered:",
        skipped_already_selected
    )

    print(
        "\nStarting position:",
        round(
            start_position,
            1
        )
    )

    print(
        "Ending position:",
        round(
            end_position,
            1
        )
    )

    if first_selected:

        print(
            "\nFirst newly selected:"
        )

        print(
            first_selected
        )

    if last_selected:

        print(
            "\nLast selected:"
        )

        print(
            last_selected
        )

    print(
        "\n================================"
    )

    print(
        "NOTHING ELSE WAS DONE"
    )

    print(
        "================================"
    )

    print(
        "Selections remain selected."
    )

    print(
        "No deselection."
    )

    print(
        "No album."
    )

    print(
        "No deletion."
    )

    print(
        "No download."
    )

    print(
        "No sharing."
    )

    input(
        "\nPress ENTER to finish..."
    )