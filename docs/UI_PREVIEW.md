# Screen layout of the running app

The app now follows the user's labelled screen structure. These are screenshots
from the tested Kivy application, with calculated results and simulated prices.

| Screen | Contents | Navigation |
| --- | --- | --- |
| 1 | App heading and parameter controls | Opens at launch; successful Optimize SMA opens 2 |
| 2 | Optimal SMA, chart, frequency cards, coverage explanation | Change parameters returns to 1; fixed bottom-left Saved SMAs and bottom-right Settings controls |
| 2a | Crossovers below the results, in the same scroll view | Starts with 5 rows; downward arrows add up to 10 at a time, through 35 |
| Expanded 2a | All selected-result crossing events | Show all opens this screen when more than 35 events exist; fixed top-left Back returns to 2 |
| 2b | Saved SMA lines in a partial bottom sheet | Opens on a new save or with the bottom-left menu; dismiss with that button, a downward handle swipe, or the dimmed area |
| 3 | Notification preferences, recipient address and preview tests | Bottom-right gear opens it; fixed top-left Back returns to 2 |

## Screen 1 — parameters

![Parameter screen](screen-parameters.png)

## Screen 2 — results

![Phone results screen](ui-phone.png)

[View the wider portrait results layout](ui-current.png).
The Hide SMA button is compact, beside the save heart and Change parameters.
The bottom navigation stays reachable while scrolling through results.

## Screen 2a — crossovers

[View the full scrollable results content, including its five-row crossover preview](screen-results-full.png).
Rows keep the original ascending session order. A short list stops at its actual
count. New optimization resets the preview to five; hiding/saving lines and
visiting another screen preserve the current preview length.

![Expanded crossover screen](screen-crossovers-expanded.png)

The full list shows every calculated event, with a fixed Back arrow even after
scrolling to the bottom. Returning preserves the results scroll position and chart.

## Screen 2b — saved lines

![Saved lines sliding over the results](screen-saved-sheet.png)

The lower sheet leaves the fixed bottom navigation accessible. Its top handle
accepts a downward swipe; the saved-line list scrolls independently below it.
The selected history icon remains option A, and the history popup still restores
the most recent ten unsaved configurations.

[View saved-line controls at phone size](ui-saved-lines.png).

## Screen 3 — settings

![Separate settings screen](screen-settings.png)

Email is still preview-only; Gmail API is the chosen future sender. Android
notification completion/device validation remain deferred until the Android
build. See [notification testing and limitations](NOTIFICATIONS.md).

The layouts were checked at five portrait sizes, including 320 pixels wide.
Native fonts can vary slightly between operating systems. Physical Android
validation is pending. No new dependency, live data or APK was added.

## Earlier design references

[Original illustrative mockup](ui-preview.png) ·
[History icon options, with A selected](HISTORY_ICON_OPTIONS.md).
