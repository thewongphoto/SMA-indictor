# Company identity and saved SMA grouping — 0.6.0

On Parameters, **Selected security** displays only the company logo and company
name. Tapping it still focuses the search field. The exchange-qualified key is
kept internally, so saved data and selection behavior are preserved.

The saved libraries on Parameters and in the Results bottom sheet both use the
same header: **logo → company name → ticker → expand/collapse arrow**. Space is
reserved for the entire ticker and arrow. A name that exceeds the remaining
width loses the whole overflowing word and all following words, replaced with
an ellipsis. It does not split a word or cover the ticker. Expanding a security
places its heading and SMA rows inside one softly tinted, rounded enclosure,
with a fine divider below the heading. Other securities have separate enclosures.
Existing View, Hide/Show, heart and phone notification controls remain available.

The recently unsaved archive uses a **20dp** logo followed by the company name,
with scenario/SMA/target details below. Main saved headers use **28dp** logos.
The archive no longer leads with the exchange/ticker. Restore keeps the exact
security and SMA configuration. All logo images are packaged locally; the
existing monogram fallback handles fictional counters and missing brand assets.

Below 380dp, parameter controls stack vertically so the logo leaves enough room
to read the company name. Wider phones retain two columns; wide desktop windows
retain four. No new landing-screen flow is implemented in this release.

## Validation

The complete suite passed **100 unit tests** and **46 running-widget UI groups**.
Inspected screenshots: [Selected security](security-identity-selected.png),
[saved SMA sheet](security-identity-sheet.png), and
[unsaved archive](security-identity-archive.png).

The running-widget smoke runner includes focused checks for 320/440/960dp
layouts, whole-word truncation, reserved tickers, company grouping in both
libraries, synchronized expansion, saved-line viewing, small archive logos and
exact restoration. Run from the repository root:

```sh
python -m scripts.smoke_ui --security-identity-only
```

For the complete calculation/persistence and Kivy checks:

```sh
python -m unittest discover -s tests -v
python -m scripts.smoke_ui
```

These are desktop/cloud checks of shared Android widgets, not physical-device
validation. The APK workflow retains the original signing identity and accepts
the `apk-v0.6.0` release tag.
