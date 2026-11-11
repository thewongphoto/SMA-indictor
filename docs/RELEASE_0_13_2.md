# 0.13.2 — visible chart changes, upward-crossing branding and iPhone checks

## Chart comparison

Below the company logo/name, the chart shows the quoted-currency change and
percentage from its first to last visible adjusted daily close. Both values
have an up/green or down/red triangle. Flat ranges are neutral. Percentage is
`(last - first) / first × 100`; it is unavailable if the first price is zero.

Preset ranges show **PAST 3M**, **PAST 6M**, etc. Pinching displays the actual
endpoint dates as **DD MMM 'YY - DD MMM 'YY**. Values follow the visible EOD
points inside the fractional viewport; missing/nonfinite edges are skipped
inside that range. No prices are interpolated and no network requests occur.
The date interval moves below the values on narrow phones when needed.

## Corrected logo and loading

The turquoise price now rises steeply from **below** the orange SMA to above
it, with the white plus at the crossing. Android legacy/adaptive icons, its
presplash, the iPhone AppIcon catalog, iOS launch image/storyboard and desktop
app icon all use the corrected master. Company/ETF issuer logos are unchanged.

During an uncached optimization, the same price/SMA paths draw left to right.
The plus appears at the crossing, followed by a short hold/fade and repeat.
The GPU effect uses elapsed time rather than a finite one-shot animation.
Native Back/Escape still cancels, and saved/cached targets open immediately.
See [screenshots and the actual rendered animation](design/ui-0.13.2/README.md).

## Failure and correction

The supplied **ios-v0.13.1** log stops in the unit-test step, before native
compilation. Its single failing test is
`test_reexport_is_deterministic_and_never_changes_the_master` in
`tests/test_android_icons.py`. The shared test suite checks both platforms'
packaging, so this Android asset check also runs on the Mac iPhone builder.

The check required a regenerated PNG to match the committed file byte for byte.
Pillow's platform wheels can encode identical pixels with different compressed
PNG bytes, even with the same pinned Pillow version. That makes file-byte
equality unsuitable for checking a regenerated image across hosts.

The corrected check requires **exact decoded pixels, dimensions and colour
mode**. It still verifies that the source master is untouched. A regression
encodes the actual adaptive icon at two different compression levels, confirms
that the files differ, and requires their image comparison to pass. Other
regressions require a one-pixel change, wrong dimensions or a different colour
mode to fail. Opacity, Android mask safety, iPhone icon-slot checks and compiled
signing-kit resource hashes remain enabled.

The 365-day analysis rules, saved data and notification behaviour remain
unchanged from 0.13.1.

## Validation

The iPhone-host Python 3.11 environment passes **332 unit checks** (two optional
NumPy checks skipped). Kivy UI checks pass for preset/pinch/reset comparisons,
320/440px layouts, matching arrows/colours, caching and unchanged request counts.
Motion checks exercise native Back, stale-worker cancellation, rendered logo
centering/brightness/plus timing and continued loops during real pure-Python
optimization, including the slower CI frame-clock configuration.

These are host/fixture checks. Native Apple and Android compilation and device
behaviour require their GitHub workflows and device testing.

## Build and installation

The new build tags are **ios-v0.13.2** and **apk-v0.13.2**. Rerunning the old
0.13.1 tag uses the old code. The shared source and Buildozer versions agree.

The native device build, signing-kit verification and simulator launches still
gate the downloadable kit. Passing Linux host checks does not establish native
Mac compilation or iPhone installation success. Wait for a successful
[iPhone workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/ios-private.yml),
then follow the [free Mac/Xcode installation guide](PRIVATE_IPHONE_INSTALLATION.md).
