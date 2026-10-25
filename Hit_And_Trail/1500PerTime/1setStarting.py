# works and finds first photo screen visible 
from playwright.sync_api import sync_playwright


# ============================================================
# CONNECT
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
    page.wait_for_timeout(1000)

    return browser, page


# ============================================================
# FIND CHECKBOX
# ============================================================

def find_checkbox(media):

    # The checkbox is in the media's surrounding container,
    # not inside the <a> itself.

    parent = media

    for level in range(10):

        try:

            checkbox = parent.locator(
                '[role="checkbox"]'
            ).first

            if checkbox.count() > 0:
                return checkbox

            parent = parent.locator("..")

        except Exception:
            return None

    return None


# ============================================================
# MAIN
# ============================================================

with sync_playwright() as p:

    browser, page = connect_to_photos(p)

    print(
        "Connected:",
        page.url
    )

    print(
        "\n================================"
    )

    print(
        "FIND FIRST ACTUALLY VISIBLE MEDIA"
    )

    print(
        "================================"
    )

    # --------------------------------------------------------
    # REAL MEDIA ONLY
    #
    # This excludes the duplicate DIV overlay.
    # --------------------------------------------------------

    locator = page.locator(
        'a[href*="/photo/"][aria-label^="Photo"], '
        'a[href*="/photo/"][aria-label^="Video"]'
    )

    total = locator.count()

    print(
        "Actual media elements:",
        total
    )

    # --------------------------------------------------------
    # GET BROWSER VIEWPORT
    # --------------------------------------------------------

    viewport = page.evaluate("""
        () => ({
            width: window.innerWidth,
            height: window.innerHeight
        })
    """)

    viewport_width = viewport["width"]
    viewport_height = viewport["height"]

    print(
        "Viewport:",
        viewport_width,
        "x",
        viewport_height
    )

    # --------------------------------------------------------
    # FIND MEDIA THAT IS PHYSICALLY INSIDE VIEWPORT
    # --------------------------------------------------------

    visible_media = []

    for i in range(total):

        try:

            media = locator.nth(i)

            box = media.bounding_box()

            if box is None:
                continue

            x = box["x"]
            y = box["y"]

            width = box["width"]
            height = box["height"]

            right = x + width
            bottom = y + height

            # ------------------------------------------------
            # IMPORTANT:
            #
            # The media must physically intersect the
            # browser viewport.
            #
            # An element at:
            #
            # y = -816
            #
            # will therefore be rejected.
            # ------------------------------------------------

            intersects_viewport = (
                right > 0
                and
                bottom > 0
                and
                x < viewport_width
                and
                y < viewport_height
            )

            if not intersects_viewport:
                continue

            label = media.get_attribute(
                "aria-label"
            )

            href = media.get_attribute(
                "href"
            )

            visible_media.append({
                "index": i,
                "element": media,
                "label": label,
                "href": href,
                "x": x,
                "y": y,
                "width": width,
                "height": height
            })

        except Exception:
            pass

    # --------------------------------------------------------
    # SORT BY ACTUAL SCREEN POSITION
    #
    # First row first.
    # Within the row: left to right.
    # --------------------------------------------------------

    visible_media.sort(
        key=lambda item: (
            item["y"],
            item["x"]
        )
    )

    print(
        "\n================================"
    )

    print(
        "ACTUALLY VISIBLE MEDIA"
    )

    print(
        "================================"
    )

    print(
        "Physically visible:",
        len(visible_media)
    )

    # --------------------------------------------------------
    # PRINT FIRST FEW
    # --------------------------------------------------------

    for number, item in enumerate(
        visible_media[:10],
        start=1
    ):

        print(
            f"\n#{number}"
        )

        print(
            "DOM index:",
            item["index"]
        )

        print(
            "Label:",
            item["label"]
        )

        print(
            "Position:",
            f"x={item['x']:.1f}, "
            f"y={item['y']:.1f}"
        )

        print(
            "Size:",
            f"{item['width']:.1f} x "
            f"{item['height']:.1f}"
        )

    # --------------------------------------------------------
    # NO MEDIA
    # --------------------------------------------------------

    if not visible_media:

        print(
            "\n❌ No media physically visible."
        )

        input(
            "\nPress ENTER to finish..."
        )

        raise SystemExit

    # --------------------------------------------------------
    # FIRST ACTUAL SCREEN MEDIA
    # --------------------------------------------------------

    target = visible_media[0]

    print(
        "\n================================"
    )

    print(
        "TARGET"
    )

    print(
        "================================"
    )

    print(
        "Selecting:"
    )

    print(
        target["label"]
    )

    print(
        "Position:",
        f"x={target['x']:.1f}, "
        f"y={target['y']:.1f}"
    )

    print(
        "Href:",
        target["href"]
    )

    # --------------------------------------------------------
    # FIND ASSOCIATED CHECKBOX
    # --------------------------------------------------------

    checkbox = find_checkbox(
        target["element"]
    )

    if checkbox is None:

        print(
            "\n❌ Checkbox not found."
        )

        input(
            "\nPress ENTER to finish..."
        )

        raise SystemExit

    before = checkbox.get_attribute(
        "aria-checked"
    )

    print(
        "\nCheckbox before:",
        before
    )

    # --------------------------------------------------------
    # CLICK ONLY TARGET
    # --------------------------------------------------------

    print(
        "\nClicking target checkbox..."
    )

    checkbox.dispatch_event(
        "click"
    )

    page.wait_for_timeout(
        500
    )

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    after = checkbox.get_attribute(
        "aria-checked"
    )

    print(
        "\n================================"
    )

    print(
        "RESULT"
    )

    print(
        "================================"
    )

    print(
        "Selected:",
        target["label"]
    )

    print(
        "Before:",
        before
    )

    print(
        "After:",
        after
    )

    if after == "true":

        print(
            "\n✓ SUCCESS"
        )

        print(
            "The top-left media that is "
            "actually inside the screen was selected."
        )

    else:

        print(
            "\n⚠ Selection was not confirmed."
        )

    print(
        "\nNo scrolling."
    )

    print(
        "No other media intentionally selected."
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