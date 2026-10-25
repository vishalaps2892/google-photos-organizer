from playwright.sync_api import sync_playwright
import time


# ============================================================
# SETTINGS
# ============================================================

TARGET_COUNT = 1500

# Scroll by part of the current viewport.
# Smaller movement gives Google Photos more overlap and
# reduces the chance of skipping lazy-loaded media.
SCROLL_RATIO = 0.40

# How frequently we check for newly loaded media.
LOAD_CHECK_INTERVAL = 0.5

# Maximum wait after a scroll before trying the next scroll.
MAX_LOAD_WAIT = 20

# Small pause after a successful selection.
SELECTION_DELAY = 0.08


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
            "Google Photos tab not found.\n"
            "Make sure Chrome is running with "
            "remote debugging on port 9222."
        )

    page.bring_to_front()
    page.wait_for_timeout(1000)

    return browser, page


# ============================================================
# FIND MAIN TIMELINE
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
                    scrollTop: el.scrollTop,
                    overflowY: getComputedStyle(el).overflowY
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
# GET CURRENTLY LOADED INDIVIDUAL MEDIA
# ============================================================

def get_media(page):

    locator = page.locator(
        '[aria-label^="Photo"], '
        '[aria-label^="Video"]'
    )

    result = []

    for i in range(locator.count()):

        try:

            media = locator.nth(i)

            if not media.is_visible():
                continue

            label = media.get_attribute(
                "aria-label"
            )

            if not label:
                continue

            if not (
                label.startswith("Photo")
                or
                label.startswith("Video")
            ):
                continue

            href = media.get_attribute(
                "href"
            )

            # A real Google Photos media item should have
            # a href. We don't want to accidentally treat
            # some surrounding element as media.
            if not href:
                continue

            result.append({
                "element": media,
                "label": label,
                "href": href
            })

        except Exception:
            pass

    return result


# ============================================================
# FIND THE CHECKBOX FOR ONE MEDIA ITEM
# ============================================================

def find_checkbox(media):

    # Try checkbox inside the media element first.
    checkbox = media.locator(
        '[role="checkbox"]'
    ).first

    if checkbox.count() > 0:
        return checkbox

    # Walk upward through the DOM.
    parent = media

    for _ in range(8):

        try:

            parent = parent.locator(
                ".."
            )

            checkbox = parent.locator(
                '[role="checkbox"]'
            ).first

            if checkbox.count() > 0:
                return checkbox

        except Exception:
            pass

    return None


# ============================================================
# SELECT ONE MEDIA ITEM
# ============================================================

def select_media(media):

    try:

        checkbox = find_checkbox(
            media
        )

        if checkbox is None:
            return False, "checkbox not found"

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # We DO NOT check aria-checked before clicking.
        #
        # The user manually handles previous batches.
        #
        # The only protection against clicking the same media
        # twice DURING THIS RUN is seen_this_run.
        # ----------------------------------------------------

        checkbox.dispatch_event(
            "click"
        )

        media.page.wait_for_timeout(
            int(SELECTION_DELAY * 1000)
        )

        # ----------------------------------------------------
        # Verify the click actually selected this item.
        # ----------------------------------------------------

        state = checkbox.get_attribute(
            "aria-checked"
        )

        if state == "true":

            return True, "selected"

        return False, (
            "click did not result in "
            "aria-checked=true"
        )

    except Exception as e:

        return False, str(e)


# ============================================================
# WAIT FOR LAZY LOADING
# ============================================================

def wait_for_new_media(
    page,
    seen_this_run
):

    waited = 0.0

    while waited < MAX_LOAD_WAIT:

        time.sleep(
            LOAD_CHECK_INTERVAL
        )

        waited += LOAD_CHECK_INTERVAL

        current = get_media(
            page
        )

        # Look for ANY media that has not been seen
        # during this run.
        #
        # This is deliberately global for this run.
        # We never forget an href until the script ends.

        new_count = 0

        for item in current:

            if item["href"] not in seen_this_run:

                new_count += 1

        if new_count > 0:

            print(
                f"✓ New media available "
                f"after {waited:.1f}s "
                f"({new_count} unseen)"
            )

            return current

        print(
            f"  Waiting for lazy-loaded media..."
            f" {waited:.1f}s"
        )

    return get_media(page)


# ============================================================
# MAIN
# ============================================================

with sync_playwright() as p:

    browser, page = connect_to_photos(p)

    print(
        "Connected:",
        page.url
    )

    timeline = find_timeline(
        page
    )

    if timeline is None:

        print(
            "ERROR: Main Google Photos "
            "timeline not found."
        )

        raise SystemExit

    print(
        "\n✓ Main timeline found"
    )

    # --------------------------------------------------------
    # DO NOT CHANGE THE CURRENT POSITION.
    # --------------------------------------------------------

    starting_position = timeline.evaluate(
        "el => el.scrollTop"
    )

    print(
        "\n================================"
    )

    print(
        "SELECT NEXT 1500 MEDIA"
    )

    print(
        "================================"
    )

    print(
        "Starting exactly at current "
        "Chrome position:"
    )

    print(
        round(
            starting_position,
            1
        )
    )

    print(
        "\nPrevious batches are NOT remembered."
    )

    print(
        "Nothing will be deselected."
    )

    print(
        "No album will be created."
    )

    print(
        "Nothing will be deleted."
    )

    print(
        "Nothing will be downloaded."
    )

    print(
        "Nothing will be shared."
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # This set exists ONLY for the current run.
    #
    # When you run the script again, it starts empty.
    #
    # We NEVER use aria-checked to skip something.
    #
    # We NEVER persist this set.
    # --------------------------------------------------------

    seen_this_run = set()

    selected_count = 0
    failed_count = 0

    first_selected = None
    last_selected = None

    # --------------------------------------------------------
    # GET FIRST LAZY-LOADED WINDOW
    # --------------------------------------------------------

    current_media = get_media(
        page
    )

    print(
        "\nCurrently loaded media:",
        len(current_media)
    )

    if not current_media:

        print(
            "\nNo Photo/Video media detected."
        )

        print(
            "Move Chrome to a position where "
            "media are visible and run again."
        )

        raise SystemExit

    # ========================================================
    # MAIN LOOP
    # ========================================================

    while selected_count < TARGET_COUNT:

        # ----------------------------------------------------
        # PROCESS EVERYTHING CURRENTLY LOADED
        # THAT HAS NOT BEEN SEEN DURING THIS RUN.
        # ----------------------------------------------------

        unseen_items = []

        for item in current_media:

            href = item["href"]

            if href in seen_this_run:
                continue

            # Mark it BEFORE clicking.
            #
            # This prevents the same href from being clicked
            # repeatedly if the DOM changes immediately.
            seen_this_run.add(href)

            unseen_items.append(
                item
            )

        print(
            "\n--------------------------------"
        )

        print(
            "CURRENT LAZY WINDOW"
        )

        print(
            "Loaded:",
            len(current_media)
        )

        print(
            "Unseen this run:",
            len(unseen_items)
        )

        print(
            "Selected so far:",
            selected_count,
            "/",
            TARGET_COUNT
        )

        # ----------------------------------------------------
        # SELECT UNSEEN MEDIA
        # ----------------------------------------------------

        for item in unseen_items:

            if selected_count >= TARGET_COUNT:
                break

            success, reason = select_media(
                item["element"]
            )

            if success:

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

            else:

                failed_count += 1

                print(
                    f"⚠ Failed: "
                    f"{item['label']}"
                    f" | {reason}"
                )

        # ----------------------------------------------------
        # 1500 REACHED
        # ----------------------------------------------------

        if selected_count >= TARGET_COUNT:
            break

        # ----------------------------------------------------
        # CURRENT TIMELINE INFORMATION
        # ----------------------------------------------------

        info = timeline.evaluate("""
            el => ({
                scrollTop: el.scrollTop,
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight
            })
        """)

        current_position = info[
            "scrollTop"
        ]

        maximum_position = (
            info["scrollHeight"]
            -
            info["clientHeight"]
        )

        # ----------------------------------------------------
        # SMALL ADAPTIVE SCROLL
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
            current_position + movement,
            maximum_position
        )

        if new_position <= current_position + 1:

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
        # WAIT FOR GOOGLE PHOTOS LAZY LOADING
        # ----------------------------------------------------

        current_media = wait_for_new_media(
            page,
            seen_this_run
        )

        # ----------------------------------------------------
        # EXTRA CHECK
        #
        # If Google Photos was slow and returned the same
        # window, we do NOT stop.
        #
        # We give it another chance.
        # ----------------------------------------------------

        unseen_after_wait = 0

        for item in current_media:

            if item["href"] not in seen_this_run:

                unseen_after_wait += 1

        if unseen_after_wait == 0:

            print(
                "\n⚠ No unseen media yet."
            )

            print(
                "Google Photos may still be loading."
            )

            time.sleep(2)

            current_media = get_media(
                page
            )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    ending_position = timeline.evaluate(
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
        "Confirmed selections:",
        selected_count,
        "/",
        TARGET_COUNT
    )

    print(
        "Selection failures:",
        failed_count
    )

    print(
        "Unique media encountered this run:",
        len(seen_this_run)
    )

    print(
        "\nStarting timeline position:",
        round(
            starting_position,
            1
        )
    )

    print(
        "Ending timeline position:",
        round(
            ending_position,
            1
        )
    )

    if first_selected:

        print(
            "\nFirst selected:"
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

    print(
        "\nNext run starts with an EMPTY "
        "seen set at whatever position "
        "you manually choose in Chrome."
    )

    input(
        "\nPress ENTER to finish..."
    )