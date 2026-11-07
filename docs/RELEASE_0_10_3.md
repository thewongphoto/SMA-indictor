# 0.10.3 — continuous loading, SMA colours and offline issuer logos

The loading indicator continues until optimization finishes or is cancelled.
The previous single Kivy animation did not honor its repeat flag. It now uses
a frame-clock loop and GPU rotation of a fixed arc. The mobile scorer yields
CPU/GIL time in small intervals and checks cancellation inside long candidates;
arithmetic, history coverage, scoring and tie rules remain unchanged.

A palette icon left of the rename pencil offers **12 colours** for a saved SMA.
The title, chart, legend and both saved menus update immediately without an API
call or optimization. Choices persist through restart, hiding and archive
restore. Automatic allocation is retained separately, so choosing a colour does
not change the defaults of later SMAs or colours already allocated by old builds.
Saved variants of the same security/period share the same plotted line colour.
An additive, transactional migration supports concurrent UI/worker opening.

Startup availability uses one small **VOO** five-day request per provider
lifetime. The live guided example always uses **Vanguard S&P 500 ETF (VOO)**,
names it on the page and leaves the selected company/analysis unchanged.

DBS previously had no packaged logo, so its initials were shown. Its company
logo now appears on every identity surface, including legacy cached records.
ETFs use recognized provider logos: VOO → Vanguard, SPY → State Street. The
bundle adds DBS plus 30 major US ETF providers, about **190 KiB** in total,
without runtime logo requests. The yfinance search/history API has no supported,
reliable logo endpoint; historic `logo_url` examples are not a dependable feed.

The [logo catalogue](OFFLINE_LOGO_CATALOGUE.md) lists coverage and source hashes.
A current AUM top-30 ranking could not be verified because this environment
blocks the ETFdb issuer-ranking page. The packaged list is explicit rather
than represented as a current league table. Unrecognized providers use initials.

Validation: **232 unit tests and 103 distinct UI checks** cover colour persistence,
legacy logo-cache recovery, VOO guide isolation and sustained spinner motion
during a real 6,800-day non-NumPy optimization. The desktop fixture recorded
more than three rotations in a 3.3-second sample; this is not measured Android
FPS. Physical-phone smoothness and banners still need installation testing.

Package and signing configuration are preserved. Price caches, saved parameters,
names, dated delivery identities and preferences remain intact. Desktop stays
interactive only; assets and colour metadata are portable to future iOS builds.

Build tag: **apk-v0.10.3**. See the [screenshots](design/ui-0.10.3/README.md),
[APK download guide](YAHOO_ANDROID_TESTING.md) and
[logo sources/coverage](OFFLINE_LOGO_CATALOGUE.md).
