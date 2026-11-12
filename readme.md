# Google Photos Organizer

> README last updated: 12 November 2026

Google Photos Organizer is a small browser-automation project that helps prepare large batches of photos and videos for transfer between Google accounts. It was created to make it easier to organize media into albums without downloading and re-uploading every file.

## The problem

My primary Google account ran out of storage, much of it taken up by photos and videos that I wanted to keep. Selecting a large library by hand felt stressful: it was easy to miss items, and downloading everything before uploading it to another account would take a long time and add an unnecessary extra step.

## The approach

Instead of downloading and re-uploading the media, this project automates selecting a batch in Google Photos and creating an album from that selection. The album can then be shared with another Google account. The recipient can open the shared album and save its items to their Google Photos library.

The project does **not** automate sharing the album, accepting the share, or saving the media in the recipient's account. Those steps are performed manually so the account owner can review the album and control access.

## What the current scripts do

The current workflow in [`Final_Run/`](Final_Run/) is:

1. Open Google Photos in a Chrome window started with remote debugging enabled.
2. Connect the selection script to that Chrome session.
3. Ask for a target number of media items and a new album name.
4. Starting from the current position in the Google Photos timeline, scan down the page and select up to the requested number of photos and videos.
5. Create a Google Photos album from the selection if the requested count is reached.
6. Manually share the album with the destination account and, from that account, save the items to its library.
7. Verify the destination account can access the saved items before deciding whether to delete anything from the source account.

The script has a maximum requested batch size of 20,000 items. It does not choose a date range or guarantee that a batch covers a particular set of photos. It starts at the timeline's current scroll position.

The [`Hit_And_Trail/`](Hit_And_Trail/) directory contains earlier experiments and diagnostic scripts used while developing the selection approach. The main workflow is in `Final_Run`.

## Requirements

- Windows
- Python 3
- Google Chrome installed at `C:\Program Files\Google\Chrome\Application\chrome.exe`
- A Google account signed in to Google Photos in the Chrome session
- Python dependencies listed in [`Final_Run/requirements.txt`](Final_Run/requirements.txt)

Install the project dependencies from the repository root:

```powershell
py -m pip install -r .\Final_Run\requirements.txt
```

The scripts connect to the installed Chrome browser over the local Chrome DevTools Protocol port `9222`; they do not use the Google Photos API.

## Usage

1. Install the requirements above.
2. Start the Chrome session and open Google Photos:

   ```powershell
   py .\Final_Run\1_connect.py
   ```

3. Sign in to the source Google account in the opened Chrome window if needed, and make sure the Google Photos timeline is visible.
4. While that Chrome session is open, run the album creation script in a second PowerShell window:

   ```powershell
   py .\Final_Run\create_album.py
   ```

5. Enter the number of items to select and a name for the new album.
6. Review the created album in Google Photos. Share it with the intended destination account using Google Photos' sharing controls.
7. In the destination account, open the shared album and use Google Photos' save/add-to-library option. Confirm the items are available in that account before removing anything from the source account.

## Important notes

- **Review before deleting.** This project organizes and selects media; it does not verify that every intended item was saved in the destination account. Keep the originals until you have checked the destination library.
- **Check selections and album contents.** The script counts items that were already selected toward the requested total, and it begins at the current timeline position. Clear unrelated selections and review the resulting album before sharing it.
- **Google Photos may change.** The automation relies on the structure and accessible labels of the Google Photos website. A site update may cause the script to stop working or behave differently. Watch the browser while it runs and stop it if the selection looks wrong.
- **Sharing is account-sensitive.** Confirm the destination account before sharing, and grant access only to people you intend to share with. The storage and ownership behavior of saved shared items may depend on Google Photos' current policies and account settings.
- **Protect the browser session.** The scripts use a local remote-debugging endpoint and a Chrome profile at `C:\ChromeDebug`. Do not expose the debugging port to a network or use a browser profile containing accounts you do not intend the script to access.
- **No transfer guarantee.** This is a personal automation project, not an official Google product or a replacement for a verified backup.

## Project status

This repository contains working scripts and development experiments, but it does not currently include an automated test suite or a complete hands-off account-to-account transfer. Always supervise the browser automation and verify important media manually.