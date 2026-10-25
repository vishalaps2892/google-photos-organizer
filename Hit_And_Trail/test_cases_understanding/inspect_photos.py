# this script only reads the entire page and prints the visible text, buttons, and links. It does not interact with the page or perform any actions.
# no scroll just print what it is next sceript we create is to check the scroll page and find 2025


from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

    # Use the existing Google Photos tab
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
        input("Press ENTER to exit...")
        raise SystemExit

    print("Connected to:", page.url)
    print("Title:", page.title())

    # Make sure the page is active
    page.bring_to_front()

    # Give the page a moment to finish loading
    page.wait_for_timeout(3000)

    print("\n--- Visible text containing 2025 ---")

    text = page.locator("body").inner_text()

    lines = text.splitlines()

    found = False

    for line in lines:
        if "2025" in line:
            print(repr(line))
            found = True

    if not found:
        print("No visible 2025 text found on the current page.")

    print("\n--- Buttons ---")

    buttons = page.locator("button")
    print("Number of buttons:", buttons.count())

    for i in range(min(buttons.count(), 30)):
        try:
            print(i, repr(buttons.nth(i).inner_text()))
        except Exception:
            pass

    print("\n--- Links ---")

    links = page.locator("a")
    print("Number of links:", links.count())

    for i in range(min(links.count(), 30)):
        try:
            print(i, repr(links.nth(i).inner_text()))
        except Exception:
            pass

    print("\nInspection complete.")
    input("Press ENTER to finish...")