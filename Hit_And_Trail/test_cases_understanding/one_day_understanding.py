from playwright.sync_api import sync_playwright


TARGET_DAYS = [
    "Fri 7 Aug",
    "Thu 6 Aug",
    "Wed 5 Aug",
]


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
    page.wait_for_timeout(1000)

    print("Connected:", page.url)

    print("\n================================")
    print("DEEP DAY STRUCTURE DIAGNOSIS")
    print("================================")

    for target_day in TARGET_DAYS:

        print("\n\n################################")
        print("TARGET:", target_day)
        print("################################")

        matches = page.get_by_text(
            target_day,
            exact=True
        )

        count = matches.count()

        print("Text matches:", count)

        if count == 0:
            print("NOT FOUND")
            continue

        element = matches.first

        # ------------------------------------------------
        # WALK UP THE DOM
        # ------------------------------------------------

        print("\n================================")
        print("ANCESTOR CHAIN")
        print("================================")

        ancestors = element.evaluate("""
            el => {

                const result = [];

                let node = el;

                for (let i = 0; i < 10 && node; i++) {

                    result.push({
                        level: i,
                        tag: node.tagName,
                        id: node.id || "",
                        className:
                            node.className?.toString() || "",
                        role:
                            node.getAttribute("role"),
                        ariaLabel:
                            node.getAttribute("aria-label"),
                        text:
                            (node.innerText || "")
                                .trim()
                                .slice(0, 300),

                        childCount:
                            node.children.length,

                        directCheckboxes:
                            node.querySelectorAll(
                                ':scope > [role="checkbox"]'
                            ).length,

                        allCheckboxes:
                            node.querySelectorAll(
                                '[role="checkbox"]'
                            ).length,

                        links:
                            node.querySelectorAll("a").length,

                        images:
                            node.querySelectorAll("img").length
                    });

                    node = node.parentElement;
                }

                return result;
            }
        """)

        for item in ancestors:

            print(
                f"""
Level {item['level']}
  tag:                {item['tag']}
  id:                 {item['id']}
  class:              {item['className']}
  role:               {item['role']}
  aria-label:         {item['ariaLabel']}
  direct checkboxes:  {item['directCheckboxes']}
  all checkboxes:     {item['allCheckboxes']}
  links:              {item['links']}
  images:             {item['images']}
  text:               {item['text']!r}
"""
            )

        # ------------------------------------------------
        # INSPECT LARGER ANCESTORS
        # ------------------------------------------------

        print("\n================================")
        print("POSSIBLE DAY CONTAINERS")
        print("================================")

        containers = element.evaluate("""
            el => {

                const result = [];

                let node = el.parentElement;

                for (let i = 0; i < 10 && node; i++) {

                    const checkboxes = [
                        ...node.querySelectorAll(
                            '[role="checkbox"]'
                        )
                    ].map(x => ({
                        tag: x.tagName,
                        aria:
                            x.getAttribute("aria-label"),
                        checked:
                            x.getAttribute("aria-checked")
                    }));

                    const media = [
                        ...node.querySelectorAll("a")
                    ].map(x => ({
                        aria:
                            x.getAttribute("aria-label"),
                        href:
                            x.getAttribute("href")
                    })).filter(x => x.aria);

                    if (
                        checkboxes.length ||
                        media.length
                    ) {

                        result.push({
                            level: i + 1,

                            tag: node.tagName,

                            className:
                                node.className?.toString()
                                || "",

                            text:
                                (node.innerText || "")
                                .trim()
                                .slice(0, 500),

                            checkboxes,

                            mediaCount:
                                media.length,

                            media:
                                media.slice(0, 20)
                        });
                    }

                    node = node.parentElement;
                }

                return result;
            }
        """)

        for container in containers:

            print("\n--------------------------------")
            print(
                "Ancestor level:",
                container["level"]
            )
            print(
                "Tag:",
                container["tag"]
            )
            print(
                "Class:",
                container["className"]
            )

            print(
                "Media count:",
                container["mediaCount"]
            )

            print("Checkboxes:")

            for checkbox in container["checkboxes"]:

                print(
                    " ",
                    checkbox
                )

            print("Media:")

            for media in container["media"]:

                print(
                    " ",
                    media
                )

        # ------------------------------------------------
        # INSPECT SIBLINGS
        # ------------------------------------------------

        print("\n================================")
        print("SIBLINGS AROUND DATE")
        print("================================")

        siblings = element.evaluate("""
            el => {

                const parent = el.parentElement;

                if (!parent) {
                    return [];
                }

                return [
                    ...parent.children
                ].map((child, index) => ({

                    index,

                    tag:
                        child.tagName,

                    className:
                        child.className?.toString()
                        || "",

                    role:
                        child.getAttribute("role"),

                    aria:
                        child.getAttribute("aria-label"),

                    text:
                        (child.innerText || "")
                        .trim()
                        .slice(0, 300),

                    checkboxes:
                        child.querySelectorAll(
                            '[role="checkbox"]'
                        ).length,

                    links:
                        child.querySelectorAll("a").length,

                    images:
                        child.querySelectorAll("img").length
                }));
            }
        """)

        for sibling in siblings:

            print(
                sibling
            )

    print("\n================================")
    print("DONE")
    print("================================")

    print("READ ONLY.")
    print("Current selection was NOT changed.")
    print("No album created.")
    print("Nothing deleted.")
    print("Nothing downloaded.")
    print("Nothing shared.")

    input("\nPress ENTER to finish...")

    