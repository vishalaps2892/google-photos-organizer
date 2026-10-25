from playwright.sync_api import sync_playwright


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
    print("\nFinding scrollable elements...\n")

    result = page.evaluate("""
    () => {

        const elements = document.querySelectorAll('*');

        const scrollables = [];

        for (const el of elements) {

            const style = getComputedStyle(el);

            const canScrollVertically =
                el.scrollHeight > el.clientHeight + 50;

            const overflowY = style.overflowY;

            if (
                canScrollVertically &&
                (
                    overflowY === 'auto' ||
                    overflowY === 'scroll' ||
                    overflowY === 'overlay'
                )
            ) {

                scrollables.push({

                    tag: el.tagName,

                    id: el.id,

                    className:
                        typeof el.className === 'string'
                            ? el.className.substring(0, 150)
                            : '',

                    ariaLabel:
                        el.getAttribute('aria-label'),

                    clientHeight:
                        el.clientHeight,

                    scrollHeight:
                        el.scrollHeight,

                    scrollTop:
                        el.scrollTop,

                    overflowY:
                        overflowY
                });
            }
        }

        return scrollables;
    }
    """)

    print("Found", len(result), "scrollable elements.\n")

    for i, item in enumerate(result):

        print(f"--- Scrollable element {i} ---")

        print("Tag:        ", item["tag"])
        print("ID:         ", repr(item["id"]))
        print("Class:      ", repr(item["className"]))
        print("ARIA label: ", repr(item["ariaLabel"]))
        print("Client H:   ", item["clientHeight"])
        print("Scroll H:   ", item["scrollHeight"])
        print("Scroll Top: ", item["scrollTop"])
        print("Overflow Y: ", item["overflowY"])

        print()

    input("Press ENTER to finish...")