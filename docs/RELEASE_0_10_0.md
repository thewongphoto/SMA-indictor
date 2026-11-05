# 0.10.0 — merged setup, named SMAs and daily Android checks

Selecting a company now stays on one builder screen. Its heading changes from
Choose a security to Set your preference, and the target/Optimize group reveals
downward over 280ms. Change parameters returns to this selected stage. The
separate parameters page and Refresh search results button are removed.

The chart's first card shows the selected target beside the line title. Saving
reveals a pencil to name the SMA. Names persist across restart, unsave/restore,
and are shown in the chart legend/inspector, library/menu rows, backtesting,
crossing details and alerts. Numeric periods remain available. Rename does not
change periods, target frequencies, line colors or delivery identities. Names
are plain text up to 60 characters; clearing one restores the default. The
dialog follows the measured keyboard/safe viewport and long legends fit phones.

The requested dates/percentage/cost paragraph is removed from the backtest cell.
Contributions, ending values, A's gain, B/C comparisons and outperformance remain.

Android checks enabled saved SMAs at **US Tue–Sat 06:30 and SGX Mon–Fri 18:30
Asia/Singapore**. Native per-slot WorkManager jobs invoke a short headless Python
service, sharing the existing adjusted-data provider, signal rules and cache.
Market/slot claims and signal/date delivery records prevent repeat attempts and
alerts. Switches/types are rechecked after fetching; missing expected closes
do not replay old signals. Requests and delivery outcomes are visible in the
scrollable request log. Background-refreshed prices are used locally on resume.

Android may delay jobs during sleep/offline or battery restrictions; this is not
an exact-alarm promise. Physical-device delivery must be tested after installation.
The shared backend is iOS-compatible, but native iPhone scheduling/delivery is
not implemented by the Android adapter. Desktop remains interactive only.

Validation: 203 unit tests and 99 UI checks (46 existing, 6 library flow, 13
desktop provider, 14 mobile transport, 12 chart refinements, 8 merged-flow/name).
Native Java compiles against Android 15/WorkManager 2.10.1 with the pinned
p4a service contract; 10 Java/Python schedule cases agree. The local compatibility
check stubs existing SDL/native host classes and is not a full APK/device run.
GitHub's build compiles the full Android package. Signing/package identity and
saved data are preserved; SQLite changes are additive.

See [flow/screenshots](design/ui-0.10/README.md) and the
[daily notification phone test guide](ANDROID_DAILY_NOTIFICATIONS.md).
