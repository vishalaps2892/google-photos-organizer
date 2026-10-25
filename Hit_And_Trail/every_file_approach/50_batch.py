from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import os
import re


BATCH_SIZE = 50
NUMBER_OF_BATCHES = 2

CHECKPOINT_FILE = "checkpoint.json"


# ============================================================
# CONNECTION
# ============================================================

def connect_to_google_photos(p):

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

    page.wait_for_timeout(1500)

    return browser, page


# ============================================================
# FIND MAIN TIMELINE
# ============================================================

def find_timeline(page):

    elements = page.locator(
        "div, c-wiz"
    )

    candidates = []

    for i in range(
        elements.count()
    ):

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
# MEDIA DATE
# ============================================================

def extract_media_date(label):

    if not label:

        return None

    match = re.search(
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{4}),?\s*"
        r"(\d{1,2}):(\d{2}):(\d{2})",
        label,
        re.IGNORECASE
    )

    if not match:

        return None

    try:

        return datetime.strptime(
            (
                f"{match.group(1)} "
                f"{match.group(2)} "
                f"{match.group(3)} "
                f"{match.group(4)}:"
                f"{match.group(5)}:"
                f"{match.group(6)}"
            ),
            "%d %b %Y %H:%M:%S"
        )

    except ValueError:

        return None


# ============================================================
# GET VISIBLE MEDIA
# ============================================================

def get_visible_media(page):

    elements = page.locator(
        '[aria-label^="Photo"], '
        '[aria-label^="Video"]'
    )

    result = []

    for i in range(
        elements.count()
    ):

        try:

            element = elements.nth(i)

            if not element.is_visible():

                continue

            label = element.get_attribute(
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

            href = element.get_attribute(
                "href"
            )

            media_date = extract_media_date(
                label
            )

            if media_date is None:

                continue

            result.append({

                "element": element,

                "label": label,

                "href": href,

                "date": media_date,

            })

        except Exception:
            pass

    return result


# ============================================================
# MEDIA ID
# ============================================================

def get_media_id(item):

    """
    IMPORTANT:

    We do NOT use the visible label as the ID.

    Two files can have exactly the same label/timestamp.

    href is preferred.

    Otherwise we create a DOM identity for the
    currently loaded element.
    """

    if item["href"]:

        return (
            "href:"
            +
            item["href"]
        )

    try:

        value = item["element"].evaluate("""
            el => {

                if (!el.dataset.gpoMediaId) {

                    el.dataset.gpoMediaId =
                        "media-" +
                        Math.random()
                        .toString(36)
                        .slice(2);

                }

                return el.dataset.gpoMediaId;
            }
        """)

        return "dom:" + value

    except Exception:

        return None


# ============================================================
# FIND MEDIA AGAIN
# ============================================================

def find_media(page, item):

    if item["href"]:

        locator = page.locator(
            f'a[href="{item["href"]}"]'
        )

        if locator.count() > 0:

            return locator.first

    # Fallback only.
    return page.locator(
        f'[aria-label="{item["label"]}"]'
    ).first


# ============================================================
# FIND INDIVIDUAL CHECKBOX
# ============================================================

def find_media_checkbox(media):

    # Direct checkbox

    checkbox = media.locator(
        '[role="checkbox"]'
    ).first

    if checkbox.count() > 0:

        return checkbox

    # Walk upward

    ancestor = media

    for _ in range(8):

        try:

            ancestor = ancestor.locator(
                ".."
            )

            checkbox = ancestor.locator(
                '[role="checkbox"]'
            ).first

            if checkbox.count() > 0:

                return checkbox

        except Exception:
            pass

    return None


# ============================================================
# SELECT ONE MEDIA
# ============================================================

def select_media(page, item):

    media = find_media(
        page,
        item
    )

    if media.count() == 0:

        return False

    try:

        checkbox = find_media_checkbox(
            media
        )

        if checkbox is None:

            try:

                media.hover(
                    timeout=1500
                )

            except Exception:
                pass

            page.wait_for_timeout(
                150
            )

            checkbox = find_media_checkbox(
                media
            )

        if checkbox is None:

            return False

        before = checkbox.get_attribute(
            "aria-checked"
        )

        if before == "true":

            return True

        checkbox.dispatch_event(
            "click"
        )

        page.wait_for_timeout(
            120
        )

        media = find_media(
            page,
            item
        )

        if media.count() == 0:

            return False

        checkbox = find_media_checkbox(
            media
        )

        if checkbox is None:

            return False

        after = checkbox.get_attribute(
            "aria-checked"
        )

        return after == "true"

    except Exception:

        return False


# ============================================================
# CHECKPOINT
# ============================================================

def save_checkpoint(data):

    temp = (
        CHECKPOINT_FILE
        +
        ".tmp"
    )

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp,
        CHECKPOINT_FILE
    )


# ============================================================
# ALBUM WORKFLOW
# ============================================================

def click_plus(page):

    candidates = [

        page.locator(
            '[aria-label="Create and add photos"]'
        ).first,

        page.locator(
            '[aria-label="Create"]'
        ).first,

        page.locator(
            '[aria-label="Add"]'
        ).first,

    ]

    for candidate in candidates:

        try:

            if (
                candidate.count() > 0
                and
                candidate.is_visible()
            ):

                print(
                    "✓ + button found"
                )

                candidate.dispatch_event(
                    "click"
                )

                page.wait_for_timeout(
                    700
                )

                return True

        except Exception:
            pass

    return False


def click_album(page):

    # Exact text

    album = page.get_by_text(
        "Album",
        exact=True
    ).last

    try:

        if (
            album.count() > 0
            and
            album.is_visible()
        ):

            album.click()

            page.wait_for_timeout(
                700
            )

            return True

    except Exception:
        pass

    # Menu fallback

    items = page.locator(
        '[role="menuitem"]'
    )

    for i in range(
        items.count()
    ):

        try:

            item = items.nth(i)

            if not item.is_visible():

                continue

            if item.inner_text().strip() == "Album":

                item.click()

                page.wait_for_timeout(
                    700
                )

                return True

        except Exception:
            pass

    return False


def click_create_album(page):

    candidates = [

        page.get_by_text(
            "Create album",
            exact=True
        ).last,

        page.get_by_text(
            "Create album"
        ).last,

    ]

    for candidate in candidates:

        try:

            if (
                candidate.count() > 0
                and
                candidate.is_visible()
            ):

                candidate.click()

                page.wait_for_timeout(
                    900
                )

                return True

        except Exception:
            pass

    return False


def enter_album_name(
    page,
    name
):

    inputs = page.locator(
        "input"
    )

    for i in range(
        inputs.count()
    ):

        try:

            input_box = inputs.nth(i)

            if not input_box.is_visible():

                continue

            input_box.fill(
                name
            )

            return True

        except Exception:
            pass

    return False


def click_upper_left_checkbox(page):

    checkboxes = page.locator(
        '[role="checkbox"]'
    )

    candidates = []

    for i in range(
        checkboxes.count()
    ):

        try:

            checkbox = checkboxes.nth(i)

            if not checkbox.is_visible():

                continue

            box = checkbox.bounding_box()

            if box is None:

                continue

            candidates.append(
                (
                    checkbox,
                    box["x"],
                    box["y"]
                )
            )

        except Exception:
            pass

    if not candidates:

        return False

    # Sort top → bottom, left → right

    candidates.sort(
        key=lambda x: (
            x[2],
            x[1]
        )
    )

    checkbox = candidates[0][0]

    checkbox.dispatch_event(
        "click"
    )

    page.wait_for_timeout(
        500
    )

    return True


def click_back(page):

    candidates = [

        page.locator(
            '[aria-label="Back"]'
        ).first,

        page.locator(
            '[aria-label="Go back"]'
        ).first,

    ]

    for candidate in candidates:

        try:

            if (
                candidate.count() > 0
                and
                candidate.is_visible()
            ):

                candidate.click()

                page.wait_for_timeout(
                    1200
                )

                return True

        except Exception:
            pass

    return False


def create_album(
    page,
    album_name
):

    print(
        "\nCreating:",
        album_name
    )

    print(
        "  +"
    )

    if not click_plus(page):

        print(
            "  ✗ + not found"
        )

        return False

    print(
        "  Album"
    )

    if not click_album(page):

        print(
            "  ✗ Album not found"
        )

        return False

    print(
        "  Create album"
    )

    if not click_create_album(page):

        print(
            "  ✗ Create album not found"
        )

        return False

    print(
        "  Enter name"
    )

    if not enter_album_name(
        page,
        album_name
    ):

        print(
            "  ✗ Name field not found"
        )

        return False

    print(
        "  Upper-left checkbox"
    )

    if not click_upper_left_checkbox(
        page
    ):

        print(
            "  ✗ Checkbox not found"
        )

        return False

    print(
        "  Back"
    )

    if not click_back(page):

        print(
            "  ✗ Back not found"
        )

        return False

    print(
        "  ✓ Album workflow complete"
    )

    return True


# ============================================================
# MAIN
# ============================================================

with sync_playwright() as p:

    browser, page = (
        connect_to_google_photos(p)
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
            "Timeline not found."
        )

        raise SystemExit

    # --------------------------------------------------------
    # ALWAYS START FROM TODAY
    # --------------------------------------------------------

    print(
        "\nMoving to timeline TOP..."
    )

    timeline.evaluate(
        "el => el.scrollTop = 0"
    )

    page.wait_for_timeout(
        2000
    )

    print(
        "✓ Starting from newest media."
    )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    processed_ids = set()

    # We intentionally don't load old checkpoint
    # media IDs for this first clean test.

    previous_date = None

    batch_number = 1

    total_selected = 0

    while (
        batch_number
        <= NUMBER_OF_BATCHES
    ):

        print(
            "\n================================"
        )

        print(
            f"BATCH {batch_number}"
        )

        print(
            "================================"
        )

        batch = []

        stuck_count = 0

        # ----------------------------------------------------
        # FIND 50 STRICTLY BACKWARD
        # ----------------------------------------------------

        while (
            len(batch)
            < BATCH_SIZE
        ):

            page.wait_for_timeout(
                700
            )

            visible = get_visible_media(
                page
            )

            # Sort newest → oldest.
            visible.sort(
                key=lambda x: x["date"],
                reverse=True
            )

            accepted_this_scan = 0

            for item in visible:

                if len(batch) >= BATCH_SIZE:

                    break

                media_id = get_media_id(
                    item
                )

                if media_id is None:

                    continue

                if media_id in processed_ids:

                    continue

                media_date = item["date"]

                # ------------------------------------------
                # CHRONOLOGICAL GUARD
                # ------------------------------------------

                if (
                    previous_date is not None
                    and
                    media_date > previous_date
                ):

                    # This media is newer than the
                    # point we have already passed.
                    #
                    # DO NOT select it.
                    continue

                # ------------------------------------------
                # SELECT
                # ------------------------------------------

                print(
                    f"  "
                    f"{len(batch)+1:02d}/"
                    f"{BATCH_SIZE}  "
                    f"{media_date:%Y-%m-%d %H:%M:%S}  "
                    f"{item['label']}"
                )

                success = select_media(
                    page,
                    item
                )

                if not success:

                    print(
                        "       ⚠ selection failed"
                    )

                    continue

                batch.append(
                    {
                        "id": media_id,
                        "label": item["label"],
                        "href": item["href"],
                        "date": media_date.isoformat()
                    }
                )

                processed_ids.add(
                    media_id
                )

                previous_date = media_date

                accepted_this_scan += 1

                total_selected += 1

                # Save checkpoint after every
                # successfully selected file.

                position = timeline.evaluate(
                    "el => el.scrollTop"
                )

                save_checkpoint({

                    "batch": batch_number,

                    "selected_in_batch":
                        len(batch),

                    "total_selected":
                        total_selected,

                    "last_media":
                        batch[-1],

                    "timeline_position":
                        position,

                })

            print(
                f"\n  Visible media: "
                f"{len(visible)}"
            )

            print(
                f"  Batch progress: "
                f"{len(batch)}/{BATCH_SIZE}"
            )

            # ------------------------------------------------
            # GOT 50
            # ------------------------------------------------

            if len(batch) >= BATCH_SIZE:

                break

            # ------------------------------------------------
            # SCROLL BACKWARD
            # ------------------------------------------------

            info = timeline.evaluate("""
                el => ({
                    top: el.scrollTop,
                    height: el.scrollHeight,
                    viewport: el.clientHeight
                })
            """)

            current = info["top"]

            maximum = (
                info["height"]
                -
                info["viewport"]
            )

            # Adaptive movement.
            movement = max(
                250,
                int(
                    info["viewport"]
                    * 0.75
                )
            )

            new_position = min(
                current + movement,
                maximum
            )

            if (
                new_position
                <= current + 1
            ):

                print(
                    "\n⚠ Timeline cannot move "
                    "backward anymore."
                )

                print(
                    "Only",
                    len(batch),
                    "items found in this run."
                )

                break

            print(
                f"  Scrolling backward: "
                f"{current:.0f} → "
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

            page.wait_for_timeout(
                1200
            )

        # ----------------------------------------------------
        # BATCH FINISHED?
        # ----------------------------------------------------

        print(
            "\n================================"
        )

        print(
            "BATCH RESULT"
        )

        print(
            "================================"
        )

        print(
            "Selected:",
            len(batch),
            "/",
            BATCH_SIZE
        )

        if len(batch) < BATCH_SIZE:

            print(
                "\n⚠ Batch did not reach 50."
            )

            print(
                "I am leaving the current "
                "selection untouched."
            )

            break

        # ----------------------------------------------------
        # SAVE FINAL BATCH CHECKPOINT
        # ----------------------------------------------------

        save_checkpoint({

            "batch": batch_number,

            "selected_in_batch":
                len(batch),

            "total_selected":
                total_selected,

            "last_media":
                batch[-1],

            "timeline_position":
                timeline.evaluate(
                    "el => el.scrollTop"
                ),

            "ready_for_album":
                True

        })

        print(
            "\n✓ 50 items selected."
        )

        print(
            "Last selected:"
        )

        print(
            " ",
            batch[-1]["label"]
        )

        # ----------------------------------------------------
        # CREATE ALBUM
        # ----------------------------------------------------

        album_name = (
            f"Test Album {batch_number}"
        )

        success = create_album(
            page,
            album_name
        )

        if not success:

            print(
                "\n⚠ Album creation failed."
            )

            print(
                "Selection has NOT been cleared."
            )

            print(
                "Checkpoint saved."
            )

            break

        print(
            "\n✓ Album created."
        )

        # ----------------------------------------------------
        # GOOGLE PHOTOS SHOULD AUTO-DESELECT
        # ----------------------------------------------------

        page.wait_for_timeout(
            1500
        )

        print(
            "\nChecking automatic deselection..."
        )

        visible = get_visible_media(
            page
        )

        selected_count = 0

        for item in visible:

            try:

                checkbox = (
                    find_media_checkbox(
                        item["element"]
                    )
                )

                if checkbox is None:

                    continue

                if (
                    checkbox.get_attribute(
                        "aria-checked"
                    )
                    == "true"
                ):

                    selected_count += 1

            except Exception:
                pass

        print(
            "Visible selected media:",
            selected_count
        )

        if selected_count > 0:

            print(
                "⚠ Google Photos still has "
                "selected media."
            )

            print(
                "Stopping before Batch 2."
            )

            break

        print(
            "✓ Selection automatically cleared."
        )

        # ----------------------------------------------------
        # BATCH COMPLETE
        # ----------------------------------------------------

        save_checkpoint({

            "completed_batch":
                batch_number,

            "last_media":
                batch[-1],

            "timeline_position":
                timeline.evaluate(
                    "el => el.scrollTop"
                ),

            "total_selected":
                total_selected,

            "ready_for_next_batch":
                True

        })

        print(
            "\n✓ Resuming from SAME timeline position."
        )

        print(
            "Next batch will continue backward."
        )

        batch_number += 1

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print(
        "\n================================"
    )

    print(
        "TEST COMPLETE"
    )

    print(
        "================================"
    )

    print(
        "Total selected:",
        total_selected
    )

    print(
        "Checkpoint:",
        os.path.abspath(
            CHECKPOINT_FILE
        )
    )

    print(
        "\nNo files downloaded."
    )

    print(
        "No files deleted."
    )

    print(
        "No files shared."
    )

    input(
        "\nPress ENTER to finish..."
    )