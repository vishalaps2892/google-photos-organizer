# this scipt is for direclty login to google phots but google restricted that
# now we are created a session and use that instead ogf it

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(
        viewport={"width": 1400, "height": 900}
    )

    page = context.new_page()

    page.goto("https://photos.google.com/", wait_until="domcontentloaded")

    print("\nGoogle Photos opened.")
    print("Log into Account A if required.")
    print("Once you can see your Google Photos library, press ENTER here.")
    input()

    print("\nCurrent page:")
    print(page.url)

    print("\nPage title:")
    print(page.title())

    input("\nPress ENTER to close the browser...")

    browser.close()