# 0.9.0 — chart and library UI refinements

Pinch gestures now keep each finger in the chart's coordinate system, update
once per display frame, preserve fractional session ranges, and ease the zoom
and vertical scale. Text textures are reused and drawing is clipped to the plot.
One finger still inspects the nearest EOD date/close/SMA; the range dropdowns
remain. This addresses the jumps seen in the supplied phone recording; physical
phone smoothness still needs confirmation after installation.

Settings stays at the top right of all seven pages. A mint outlined magnifier
with a small floating plus opens Choose a security from Results. Saved SMAs no
longer has a hamburger. All security groups start collapsed after a cold launch.
See the [screenshots and icon](design/ui-0.9/README.md).

Optimize opens a matching saved target's exact period immediately, or reuses an
unsaved analysis for identical prices/dates and target. This choice persists
across restarts. New prices/dates invalidate an unsaved choice; saved periods
stay fixed. No extra data request is made by Optimize. The unused Custom +
button is removed from live Parameters; the numeric Custom frequency remains.

SMA colors are stored per security/period. Existing saved lines receive colors
in original save order: amber first, then distinct colors. Viewing, hiding,
unsaving/restoring or relaunching never changes those assignments. The same
palette can be reused for another security. The migrations are additive and
preserve saved parameters, visibility, preferences and downloaded history.

The date axis measures labels and chooses spaced month/year or year-only ticks
that fit the available width. Live screens, connection messages and the
copyable request report use neutral data labels. The live guided example now
uses downloaded history, including an explicit SPY search/history load if no
company is selected. Offline example saves remain separate in storage.

Backtesting explains USD 100 per buy, elapsed years, crossing count and total
contributed. Scenario A shows its percentage return against contributions with
a green upward arrow for gains, red downward arrow for losses, and N/A for no
buys. B/C percentages remain relative to A. USD comparisons apply quotation-price
returns and exclude currency movements; no historical FX conversion is implied.
Crossing fills remain daily-line estimates and cash dividends/fees/taxes remain
excluded.

The request log is a touch-scrollable list of bounded cards. Load older calls
reads another 100 local entries without making API requests. Copy includes the
currently loaded report; Back dismisses the log. No credentials or response
bodies are included.

Validation: **172 unit tests**, **46 existing UI groups**, **6 library-flow
groups**, **14 mobile transport/UI groups** and **12 new UI refinement groups**.
HTTP fixtures are controlled test responses, not live market observations or
physical-device measurements. The package/signing identity and dependencies
remain unchanged. Background fetching/notification delivery remain deferred.
The `apk-v0.9.0` tag requests GitHub compilation; a pushed tag does not establish
a successful APK build.
