# 0.7.0 — library-first UI

Approved for release on 3 November 2026 (Singapore).

## Changes

- Launch into **My SMA library**. Saved lines appear immediately when present;
  otherwise the first card asks **“New to moving averages and upward crossing
  buy signals?”** and offers the guided example.
- Use **New analysis → Search → Parameters → Results**. Search still requires
  Enter/Submit, and selecting a match loads its simulated history.
- Use fixed top navigation and Back instead of a Home/Saved/Learn bottom bar.
  Saved-line View restores the exact period and target directly from Library.
- Expand **Custom** on Parameters for the fictional price-pattern setting.
- Explore the isolated three-year guide at different crossing frequencies. It
  uses the real optimizer and backtest engine, includes both recoveries and
  renewed declines, and explains that crossing signals do not guarantee gains.
- Show the **company logo and company name** at the top of the main chart.
  Names shorten at whole-word boundaries; missing brand images use initials.
- Retain saved company groups, archive/restore, phone notifications, EOD
  inspection, pinch zoom, quick chart ranges and the existing comparisons.
- Leaving Search/Parameters cancels pending work so late responses do not
  reopen a page or replace the user's current selection.

The approved [full-app flow and screen captures](design/library-first-review/README.md)
cover the guide, search, parameters, results, saved controls, comparisons,
crossing details, archive and Settings.

## Validation and Android build

The release checks comprise **102 unit tests**, **46 full Kivy UI regression
groups** and **6 focused library-flow groups**. Both UI runners execute before
APK packaging, and their logs/reports are included in the build artifact.
Cloud validation uses desktop Kivy; a physical Android test of this version is
still required after installation.

Tag **`apk-v0.7.0`** requests the existing
[Build Android test APK workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml).
Download **sma-android-test** from a successful run's Artifacts section and
extract its APK. A pushed tag is not evidence that packaging has completed.

Package `org.thewongphoto.smaanalyzer`, ARM64 target, Android minimum 8.0 and
existing signing configuration are preserved. The workflow requires the
original signing key and refuses to generate a replacement if it is missing.
Install over the previous APK with the same signing identity to retain saves.

Prices, dates and search histories remain simulated. Twelve Data integration
is still pending. No account, email setup or API key is required for this UI.
