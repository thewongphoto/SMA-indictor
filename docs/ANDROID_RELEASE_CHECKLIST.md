# Android release checklist

Current source: **0.13.5**. Automatically publish completed, validated Android
changes unless the user asks to hold them. Native iOS releases are paused.

## Before publishing

1. Match `sma_analyzer/version.py` and `buildozer.spec`. Preserve package
   `org.thewongphoto.smaanalyzer`, signing identity and saved-data compatibility.
2. Run unit tests with host validation requirements, then every UI gate below.
   Do not omit the offline/default startup test just because live fixtures pass.
3. Run `python -m scripts.check_repository_docs` and `git diff --check`.
4. Commit and push main with a fresh `apk-v*` tag. Confirm Git reports the
   successful remote update before describing it as published. Never overwrite
   released tags or create an `ios-v*` tag while native iOS releases are paused.
5. Check Actions for native compilation success. Only then describe its APK as
   ready to download. Source/tag publication alone is not that confirmation.

```sh
python -m unittest discover -s tests -v
python -m scripts.smoke_ui
python -m scripts.smoke_ui --library-flow-only
python -m scripts.smoke_mobile_yahoo_ui
python -m scripts.smoke_ui_refinements
python -m scripts.smoke_ui_flow
python -m scripts.smoke_ui_motion
KCFG_GRAPHICS_MAXFPS=12 python -m scripts.smoke_ui_color_logos
python -m scripts.smoke_notification_jobs
```

Install `requirements-android.txt`, `requirements.txt` and
`requirements-validation.txt` in a separate Python 3.11 Linux environment for
APK host validation. The workflow supplies Xvfb/X11 and software GL. A headless
local run can use `SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1` with writable
KIVY_HOME and XDG_CACHE_HOME directories. These are fixture tests, not live API
or phone delivery tests. [Native source pins](MOBILE_NATIVE_SOURCES.md).

The Ubuntu 22.04 workflow uses `bash scripts/install_android_deps.sh` for
signed HTTPS repositories and fresh package indexes. Its setup log is retained
as `android-deps.log` even when dependency installation fails. Do not disable
APT signature or TLS verification to work around a mirror/network failure.

## Physical phone checks

| Area | Expected behaviour |
| --- | --- |
| Upgrade | Install over the existing app; saved periods, colours, names, cache and alert choices survive. |
| Search | No keystroke requests; Enter/Submit searches; selection loads real adjusted history; stale responses cannot replace newer selections. |
| Parameters | Selection and target share one page; keyboard stays usable; matching saved/cached choices open immediately. |
| Calculation | Continuous logo paths/plus, dimmed background, responsive native Back cancellation. |
| Library | All companies/SMAs appear, start collapsed, and retain colours/visibility/preferences; View uses the exact period. |
| Chart | Smooth pinch, EOD inspector, nonoverlapping month/year ticks, ranges and endpoint changes stay consistent. |
| Backtest/guide | Independent horizons, Custom input, contribution/ending comparisons, VOO default 4/year and Max. |
| Sheets/navigation | Settings top-right; archive/help/saved drawer animation; Back dismisses editor/sheet before page navigation. |
| Persistence | Restart and offline saved View retain data; explicit market-cache clear keeps saved parameters. |
| Notifications | All three types, manual test, bound-service background test and four SGT schedules; disabled settings respected. |
| Diagnostics | Scroll/copy old and new data/notification rows; no raw secrets; duplicate/failure/expiry paths logged. |

Record the actual artifact version, device/Android version and observed results.
Do not carry a result from an older APK forward as if the new build was tested.
