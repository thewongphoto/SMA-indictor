# Android app (Python/Kivy): implementation guidance

Restyle and restructure the UI only. Do not change calculations, the SQLite schema of existing tables, saved data, notification rules or build/signing configuration.

## Keep unchanged

`engine.py`, `policy.py`, `backtest.py`, `schedule.py`, `notifications.py` rules and wording, `storage.py` tables and migrations, `palette.py` colour order, `line_names.py` limits, market-data and cache behaviour (`yahoo.py`, `mobile_yahoo.py`, `market_cache.py`), Android WorkManager and service code, `android/` manifests, Buildozer and signing.

## Map design to Kivy

- **Units**: every px value in [design-tokens.md](design-tokens.md) is a `dp` value; type sizes are `sp`.
- **Colours**: convert hex to Kivy RGBA (0–1). Put the UI tokens in one module (for example a new `sma_analyzer/theme.py`) rather than scattering literals. SMA line colours stay in `palette.py`.
- **Font**: register Manrope with `LabelBase.register` (Regular/500, SemiBold/600, Bold/700, ExtraBold/800). Bundle the TTF files (SIL OFL 1.1; include the licence text).
- **Tabs**: a `ScreenManager` per tab (Home, Charts, Alerts, Settings) under one bottom bar. Remove the gear entry points and the Saved SMAs bottom sheet once Home covers it.
- **Safe area**: pad the tab bar by the Android navigation/gesture bar inset.
- **Keyboard**: `Window.softinput_mode = "below_target"` so the search and email fields stay visible.
- **Back**: Android Back pops the current tab's stack, closes sheets and cancels the optimising job (as now), plus the visible Back and Cancel buttons.
- **Rounded cards**: `RoundedRectangle` with the token radii. Switches: custom widget 44 × 26 dp in a 44 dp tall touch area.
- **Logo animation**: keep `app_logo.py` and `logo_motion.py`; place them in the new startup screen and optimising card.

## Screen by screen

| Screen | Source to change | Notes |
| --- | --- | --- |
| 01 Home | `app.py` library page | Group by security, sort below-line securities first, expandable cards. |
| 02/02b | `app.py` results page, `chart.py` | Status sentence, visible Custom segment, text Save, backtest restyle. Chart drawing logic unchanged. |
| 03 Alerts | `app.py` notification settings | New tab. Model follows the open decision on per-line alert types. |
| 04 Settings | `app.py` settings builders | Add contact email and legal card; keep all diagnostics. |
| 05/07 | `navigation.py` `OptimizationOverlay`, app start | Add the Cancel button. |
| 06 | new first-run screen | Shown once; store a "first run done" preference. |
| 08/09 | `widgets.py` `ColorOption`, rename flow | Use `LineStore.rename` and `LineStore.set_color` as now. |
| 10/11 | `app.py` search page | Keep Enter/Submit-only search and query cache. Show company names and logos. |

## New data (needs a decision before coding)

- Contact email: a new `preferences` key, separate from `NotificationSettings.email`.
- First-run flag and install ID: new `preferences` keys.
- Company logos: bundled image files keyed by symbol, with a letter-circle fallback.
