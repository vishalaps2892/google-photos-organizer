import json

from playwright.sync_api import sync_playwright


PLUS_BUTTON_NAME = "Create or add to album"


def find_photos_page(browser):

	for context in browser.contexts:

		for page in context.pages:

			if "photos.google.com" in page.url:
				return page

	raise RuntimeError("Google Photos tab not found.")


def get_plus_button(page):

	return page.get_by_role(
		"button",
		name=PLUS_BUTTON_NAME,
		exact=True
	)


def click_new_album_option(page):

	album_menu_item = page.get_by_role(
		"menuitem",
		name="Album",
		exact=True
	)

	if album_menu_item.count() != 1 or not album_menu_item.is_visible():
		raise RuntimeError("Expected one visible 'Album' menu item.")

	album_menu_item.click(timeout=5000)

	new_album_option = page.get_by_role(
		"option",
		name="New album",
		exact=True
	)

	new_album_option.wait_for(state="visible", timeout=5000)

	if new_album_option.count() != 1:
		raise RuntimeError("Expected one 'New album' option.")

	new_album_option.click(timeout=5000)


def get_album_name():

	while True:
		album_name = input("Enter the new album name: ").strip()

		if album_name:
			return album_name

		print("Album name cannot be empty.")


def name_and_create_album(page, album_name):

	name_input = page.get_by_role(
		"textbox",
		name="Edit album name",
		exact=True
	)

	name_input.wait_for(state="visible", timeout=10000)

	if name_input.count() != 1:
		raise RuntimeError("Expected one visible album name field.")

	name_input.fill(album_name)

	done_button = page.get_by_role(
		"button",
		name="Done",
		exact=True
	)

	if done_button.count() != 1 or not done_button.is_visible():
		raise RuntimeError("Expected one visible 'Done' button.")

	done_button.click(timeout=5000)


def inspect_plus_icon(page):

	return page.evaluate("""
		() => {

			const isVisible = element => {
				const rect = element.getBoundingClientRect();

				return (
					rect.width > 0 &&
					rect.height > 0 &&
					rect.bottom > 0 &&
					rect.right > 0 &&
					rect.top < window.innerHeight &&
					rect.left < window.innerWidth
				);
			};

			const describe = element => ({
				tag: element.tagName,
				className: String(element.className || "").slice(0, 160),
				role: element.getAttribute("role"),
				ariaLabel: element.getAttribute("aria-label"),
				title: element.getAttribute("title"),
				text: (element.innerText || "")
					.trim()
					.replace(/\\s+/g, " ")
					.slice(0, 100),
				visible: isVisible(element)
			});

			const addControls = Array.from(
				document.querySelectorAll(
					'button, [role="button"]'
				)
			)
				.filter(isVisible)
				.map(element => ({
					...describe(element),
					svgPaths: Array.from(
						element.querySelectorAll("svg path")
					)
						.slice(0, 3)
						.map(path => path.getAttribute("d"))
				}))
				.filter(control =>
					/add|plus|album|create/i.test(
						[
							control.ariaLabel,
							control.title,
							control.text
						].filter(Boolean).join(" ")
					)
				);

			return {
				url: location.href,
				oldClassMatchCount: document.querySelectorAll(
					".pYTkkf-Bz112c-RLmnJb"
				).length,
				addControls
			};
		}
	""")


def main():

	album_name = get_album_name()

	with sync_playwright() as playwright:

		browser = playwright.chromium.connect_over_cdp(
			"http://127.0.0.1:9222"
		)

		page = find_photos_page(browser)
		report = inspect_plus_icon(page)
		plus_button = get_plus_button(page)
		button_count = plus_button.count()
		button_visible = (
			button_count == 1 and plus_button.is_visible()
		)

		report["albumPlusButtonCount"] = button_count
		report["albumPlusButtonVisible"] = button_visible

		print(json.dumps(report, indent=2))

		if not button_visible:
			raise RuntimeError(
				"Expected exactly one visible 'Create or add to album' button."
			)

		plus_button.click(timeout=5000)
		print("Clicked 'Create or add to album'.")

		click_new_album_option(page)
		print("Selected 'Album' then 'New album'.")

		name_and_create_album(page, album_name)
		print(f"Clicked 'Done' to create album '{album_name}'.")


if __name__ == "__main__":
	main()
