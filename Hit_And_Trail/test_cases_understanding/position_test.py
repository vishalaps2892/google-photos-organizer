# currenty our script finds the files from where our current scroll is till end 
# but we wnat the entire year instead of from that postion till end to starting to end

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

    # Find the main timeline.
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
        print("Timeline not found.")
        raise SystemExit

    info = timeline.evaluate("""
        el => ({
            scrollTop: el.scrollTop,
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight
        })
    """)

    print("================================")
    print("TIMELINE INFORMATION")
    print("================================")

    print("Scroll height:", info["scrollHeight"])
    print("Viewport:", info["clientHeight"])
    print("Current position:", info["scrollTop"])

    # Move to the top.
    print("\nMoving to timeline TOP...")

    timeline.evaluate("""
        el => {
            el.scrollTop = 0;
        }
    """)

    # Wait for Google Photos to render.
    page.wait_for_timeout(3000)

    info = timeline.evaluate("""
        el => ({
            scrollTop: el.scrollTop,
            scrollHeight: el.scrollHeight
        })
    """)

    print("New position:", info["scrollTop"])

    print("\n================================")
    print("DATES AT TOP")
    print("================================")

    days = get_day_selectors(page)

    if days:

        for day in days:
            print(day)

    else:

        print("No day selectors currently loaded.")

    print("\nThis was READ ONLY.")
    print("Nothing was selected.")
    print("No album was created.")

    input("\nPress ENTER to finish...")