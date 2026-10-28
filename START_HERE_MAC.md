# Open the app on your Mac

These instructions assume you have never used Python or Kivy. Python runs the
program; Kivy draws the app's screen. You do not need to edit any code.

## 1. Check Python

You have already confirmed that `python3.12 --version` prints `Python 3.12.10`.
That is the version to use for these instructions.

## 2. Get the project from GitHub

1. Open <https://github.com/thewongphoto/SMA-indictor> in your Mac's browser.
2. Sign in to your own GitHub account if the repository is private.
3. Select the `main` branch if it is not already selected.
4. Click the green **Code** button, then **Download ZIP**.
5. In Finder, open **Downloads** and double-click the downloaded ZIP.
6. Open the extracted folder, normally called **SMA-indictor-main**. You should
   see `main.py`, `requirements.txt`, and this document inside it.

## 3. Open Terminal in the project folder

1. Press **Command + Space**, type **Terminal**, and press **Return**.
2. Type `cd` followed by one space. Do not press Return yet.
3. Drag the extracted **SMA-indictor-main** folder from Finder into Terminal.
   This inserts the folder's path for you.
4. Now press **Return**. Terminal is ready to run commands in that folder.

## 4. Prepare the app

Copy this line into Terminal and press Return:

```sh
python3.12 -m venv .venv
```

This creates a private place for the app's Python packages. It usually finishes
without printing anything. Then copy this line and press Return:

```sh
.venv/bin/python -m pip install -r requirements.txt
```

Wait until the installation finishes and Terminal is ready for another command.
This downloads Kivy and its supporting packages from the Python package index.
It does not download stock prices or ask for any financial accounts.

## 5. Open the app

Copy this line and press Return:

```sh
.venv/bin/python main.py
```

A window titled **SMA Stock Analyzer** should open. Leave Terminal open while
you use the app.

1. Select **DEMO-SGX** and **Oscillating**.
2. Choose **12** crossings per year.
3. Click **Optimize SMA**.
4. Scroll down to see the statistics and crossover table.
5. Click **Save SMA line**. Try a different target and optimize again to compare
   lines. These controls are in the Optimal SMA card above the chart. The
   crossing count is in section 03, below the two frequency cards.
6. To zoom, click and hold inside the chart, drag left or right, then release.
   The selected range is shaded, with a green line on the left and a red line
   on the right. Click **Zoom out** beside the chart title to return to the selected timeline
   again. Choose Max in the dropdown to see the full history. The zoom-out button appears only while zoomed.

The chart now starts at 1Y out of five years of simulated data. Use the rounded
dropdown below the counter title for 3Y, 5Y or Max. The whole button, including
its arrow, opens the menu. Options disappear if there is insufficient history.
Changing the view does not change the full-history analysis.

The actual frequency now excludes the SMA's warm-up and missing observations.
For example, DEMO-SGX Sideways at target 12 should show SMA 254 and 31.31/year,
with 125 crossings over 1,006 usable comparisons. That is the closest eligible
result, even though it does not match 12. The app has 1,260 mock sessions.

Every price is simulated. These are fictional counters, not real market data.
Matching crossing frequency does not demonstrate a profitable strategy.

Close the app window when finished. To open it another day, repeat the Terminal
folder step and run `.venv/bin/python main.py`; installation is needed only once
for this downloaded copy.

## Optional: run the tests

After closing the app, run this in the same Terminal folder:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The current test suite contains 44 tests, including checks that the active app
uses the agreed warm-up-adjusted frequency and automatic SMA cap. Successful
output ends with `OK`.

## Getting a newer version from GitHub

If you downloaded the project as a ZIP, edits on GitHub do not automatically
update your Mac's copy. Download the ZIP again using step 2 and extract it to
a new folder, keeping the old copy until the new one opens successfully. Then
repeat steps 3–5 for the new folder. Choose **Keep Both** if Finder asks about
an existing folder. Saved SMA lines live in your Mac's application data folder,
so they remain available when the updated app opens under the same Mac account.

## If something goes wrong

- **Certificate/SSL error during installation:** in Finder, open
  **Applications > Python 3.12**, double-click **Install Certificates.command**,
  let it finish, then retry the package installation command.
- **Cannot find requirements.txt or main.py:** repeat step 3 using the folder
  that contains both files.
- **Other error:** copy the last few lines from Terminal into the chat. Include
  the command you ran. There is no need to reinstall everything first.

This stage runs on your Mac. Packaging an installable Android app is a later step.
