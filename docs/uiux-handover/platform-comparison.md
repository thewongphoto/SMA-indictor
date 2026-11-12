# Android (Kivy) and iPhone web: screen-by-screen

Both apps share the same visual identity, screen structure, wording and core interactions. Differences below are only those the platforms force.

| Screen | Android app (Kivy) | iPhone web app (Vercel) |
| --- | --- | --- |
| 05 Startup | Shown while Python/Kivy starts and the SQLite store opens. | Shown while the app shell and cached data load. With a service worker it also appears offline. Keep it under about 1 s on repeat visits. |
| 06 First open email | Stored locally; the server endpoint is called when online, queued if offline. | Same. Stored in IndexedDB and on the server. iPhone may clear website data; the server copy is the record. |
| 01 Home | Same. Tab bar sits above the Android gesture/navigation bar inset. | Same. Tab bar adds `env(safe-area-inset-bottom)`. In a Safari tab, Safari's toolbar sits below it (screen 17). |
| 10/11 Search | Enter/Search only; results cached in SQLite (existing behaviour). | Enter/Search only; same-origin API; cache results in IndexedDB. Input font 16 px. Keyboard return key labelled Search (`enterkeyhint="search"`). |
| 02 SMA detail / chart | Existing Kivy chart; restyle colours only. Pinch and one-finger inspection as today. | Touch chart with `touch-action: none` on the chart only; two-finger pinch, one-finger press-and-drag inspection. Leave a 16 px gap from screen edges so Safari's edge swipe still works in a tab. |
| 02b Backtest | Runs locally with `backtest.py`. | Runs on the server or Python worker with `backtest.py`; show 07-style loading if it takes more than about 300 ms. |
| 07 Optimising | Local job; Cancel stops it. | Server job; Cancel calls the job's cancel endpoint and ignores stale results. |
| 08/09 Lines | Same. Bottom sheet over the chart. | Same. Sheet scroll uses `overscroll-behavior: contain`; sheet padding adds the bottom safe area. |
| 03 Alerts | WorkManager background checks at the SGT schedules. Android permission prompt on Android 13+. | **Only in the Home Screen app on iOS 16.4+**, after the user taps "Enable notifications" (screen 18). A server scheduler checks prices and sends Web Push. In a Safari tab, show how to add to Home Screen instead. |
| 04 Settings | Keep all Android tests and diagnostics. | Replace the Android tests with "Send test notification" (server push). Add "Export saved lines" and "Import" because iPhone may clear website data. Keep Request log and Clear downloaded data. |
| 12–16 States | Same designs. Offline uses the existing SQLite cache. | Same designs. Offline uses the service-worker app shell and IndexedDB cache. |
| 17/18 Display | n/a | Safari tab: browser toolbars reduce height; use `100dvh`, never `100vh`. Home Screen: standalone, full height, status bar overlays the top, so pad by `env(safe-area-inset-top)`. |

## Features that work differently on the web

Nothing native is automatically available on the web. Each of these needs separate web work:

- **Notifications**: Web Push only, only from the Home Screen app, iOS 16.4 or later, only after a user tap. Delivery timing is controlled by iOS. A Safari tab cannot receive them.
- **Background activity**: the iPhone does not run the app in the background. All scheduled checks run on a server.
- **Storage**: IndexedDB can be cleared by iOS. Saved lines must be synced to the server and exportable. Android's SQLite data does not transfer automatically.
- **Offline**: requires a service worker that caches the app shell. New searches and calculations need a connection.
- **Market data**: requests come from a server, not the phone. Provider limits and blocks from cloud IPs must be tested (see `docs/MARKET_DATA.md`).
