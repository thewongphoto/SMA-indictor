# Open the app on your Mac

The latest Kivy desktop preview is available on GitHub's **main** branch.
These instructions download and run that version. No Android APK build is needed.
For the exact simulation rules, see [Desktop preview](docs/DESKTOP_PREVIEW.md).

These instructions assume you have never used Python or Kivy. Python runs the
program; Kivy draws the app's screen. You do not need to edit any code.

## 1. Check Python

Open Terminal and run:

```sh
python3.12 --version
```

Use Python **3.12**. Your previously confirmed Python 3.12.10 is suitable.

## 2. Get the project from GitHub

1. Open <https://github.com/thewongphoto/SMA-indictor> in your Mac's browser.
2. Sign in to your own GitHub account if the repository is private.
3. Select the **main** branch if it is not already selected.
4. Click the green **Code** button, then **Download ZIP**.
5. In Finder, open **Downloads** and double-click the downloaded ZIP.
6. Open the extracted folder, normally called **SMA-indictor-main**. You should
   see `main.py`, `requirements.txt`, `run-desktop.command`, and this document.

If you already have an older download, extract the new one into a separate
folder and choose **Keep Both** if Finder asks. GitHub changes do not update
an existing ZIP download or the folder you extracted from it.

## 3. Open Terminal in the project folder

1. Press **Command + Space**, type **Terminal**, and press **Return**.
2. Type `cd` followed by one space. Do not press Return yet.
3. Drag the newly extracted **SMA-indictor-main** folder from Finder into Terminal.
   This inserts the folder's path for you.
4. Press **Return**. Terminal is ready to run commands in that folder.

## 4. Prepare and open the app

Copy this line into Terminal and press Return:

```sh
bash run-desktop.command
```

The launcher creates `.venv` if needed, installs Kivy and the other desktop
requirements, then opens a window titled **SMA Stock Analyzer**. The first launch
needs internet access to download dependencies. It does not download stock prices
or ask for financial accounts. Leave Terminal open while you use the app.

The launcher puts this preview's saved SMA data in `.local/preview-data` inside
the downloaded project folder. It leaves data from your phone or an earlier
manually launched desktop app untouched.

## 5. Try the desktop preview

1. Select **DEMO-SGX**, **Oscillating**, and **12** crossings per year.
2. Click **Optimize SMA**. The app moves from Parameters to Results.
3. Plus markers show estimated price/SMA intersections. Drag the mouse across
   the chart to inspect the nearest EOD date, price, and SMA value; this does
   not zoom. Use **1Y**, **3Y**, **5Y**, or **Max** for quick views. Two-finger
   zoom requires an input device/provider that supplies two touches to Kivy;
   a normal laptop mouse supplies one pointer. **Zoom out** restores a preset.
4. Scroll to section **03 / Backtesting**. Its independent period dropdown sits
   beside **If you invested $100 for the past:**. Each scenario buys N times:
   a at upward crossings, b at equal-period starts (DCA), and c using the most
   common whole-dollar average-price group among 500 random samples. Each
   purchase invests $100. Only ending dollar values are displayed, with b/c
   percentage differences relative to a. Click either circled **i** for help.
5. Click the outline heart in the Optimal SMA card to save a line. Try another
   target or security, optimize, and save again.
6. Open **Saved SMAs** with the bottom-left menu. Click the down arrow beside
   a security to expand its saved SMA rows; click the up arrow to collapse them.
   Each row has View, Hide/Show, heart, and notification controls. The saved
   library on Parameters uses the same groups and shares their expanded state.
7. Click **View** to open a saved line's exact parameters. **Change parameters**
   returns to the form. The backtesting panel's **View all upward crossings**
   button opens the full event list; its Back arrow returns to Results.

The app has 1,260 mock sessions. Every price and date is simulated. Crossing prices
are interpolated from daily line segments, not observed intraday trades. The SMA
optimizer matches a chosen crossing frequency rather than maximizing returns.
See the desktop guide for the DCA schedule, random mode and price-rank definition.

Close the window when finished. On later visits, repeat step 3 and run
`bash run-desktop.command` again. That reuses this copy's environment and saves.

## Try notification previews

Use the bottom-right gear on Results to open **Notification Settings**. Enable
Phone Buy or Impending buy, return to Results, expand the security in Saved SMAs,
and turn on that line's phone notification control. In Settings, enter a session
number and press **Preview EOD alerts** to see simulated phone text. Preview
sends nothing. Real phone delivery requires the Android build. Email/Gmail
controls and sending are removed in version 0.4.0.

To unsave a line, click its red heart. The history/clock icon in section 02 lets
you restore the last ten unsaved lines. Hide/Show only controls the chart line;
notification preferences are separate.

## Optional: run the tests

After closing the app, run this in the same Terminal folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The current suite has **93 tests**. Successful output ends with `OK`.
For the focused running-widget desktop checks, use:

```sh
bash run-desktop.command --smoke-test --preview-rules-only
```

That uses a temporary test database and exits when the checks finish.

## Getting a newer version from GitHub

Download the ZIP again using step 2 and extract it to a new folder. Keep the old
folder until the new version opens successfully, then repeat steps 3–4.

The launcher keeps preview saves **inside each downloaded folder**, so a new
folder starts with a fresh preview database. To carry saves forward, close both
copies and copy the old `.local/preview-data` directory to the same location in
the new folder before its first launch. Keep the old directory as a backup.
In Finder, **Command + Shift + .** shows hidden folders such as `.local`.
If you already launched the new copy and saved lines there, keep both databases
and ask for help combining them rather than overwriting either one.

Older desktop copies launched directly with `python main.py` used Kivy's per-user
application data directory; those files are not deleted or automatically moved
by this launcher.

## If something goes wrong

- **Certificate/SSL error during installation:** in Finder, open
  **Applications > Python 3.12**, double-click **Install Certificates.command**,
  let it finish, then retry the launcher command.
- **Cannot find run-desktop.command, requirements.txt or main.py:** repeat step 3
  using the newly downloaded folder that contains those files.
- **Other error:** copy the last few lines from Terminal into the chat, including
  the command you ran. There is no need to reinstall everything first.
