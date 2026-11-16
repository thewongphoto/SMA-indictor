# Custom price history

Implemented for Android and the Vercel iPhone web app in 0.19.0 from the supplied
“Custom price history for SMA signals: UX proposal” PDF and
[wireframe screens 19–26](https://claude.ai/artifact/KyixDd8An3mJuW9Xaye3ar#artboard-386855d29d11).
Screen 24 incorporates the owner's correction: **“Keeps both. The new line
starts with alerts on.”**

## Use

1. Select a security and target on Set your preference.
2. Leave Price history used at All available, or tap it to choose Last 10/5/3
   years or Custom dates. The mini chart highlights the window and the readout
   counts actual sessions. Invalid dates, too few sessions and insufficient
   complete prices block Apply. Cancel discards the draft.
3. Calculate explicitly. Neither changing a preset nor editing dates fetches
   prices or starts optimization. The picker reuses already downloaded history.
4. To refine a result, use the same row on Charts. The earlier result stays
   visible and dimmed; Save is disabled until Recalculate matches the new dates.
5. If that result came from a saved line, choose Update this line or Save as a
   new line. Update retains its ID, name, colour, visibility and alert choices.
   New keeps both and turns on the new line's phone and three signal switches.
   Device permission and master switches still control delivery.

Presets become exact dates, including their final downloaded close. They are
frozen when saved. All available remains the default and adds no date tag.
Custom lines show a neutral year tag on Home, scoped fallback names, full dates
in Saved lines and Alerts, scoped status/notification text and a labelled chart
bracket with unused prices dimmed. Chart range chips and investment horizons
still control their own views; they do not change calculation dates.

## Calculation and compatibility

`sma_analyzer/history_window.py` is shared with browser Python and the optional
legacy worker. The selected slice drives optimizer eligibility, warm-up,
crossings and annual exposure. Candidate caps, gaps, exact ties, NumPy parity and
365-day live frequency stay unchanged. Four sessions are the engine's structural
minimum; gaps/coverage can require a wider window. There is no invented two-year
reliability rule and no profitability claim.

The chosen period's chart series and current alerts continue across full
downloaded history. Future price updates do not retune saved periods or move
custom dates. Backtesting remains independently scoped by its investment horizon.

Custom dates join saved/cache/notification identities. SQLite migration copies
existing rows and IDs; default delivery keys retain their exact previous format.
Archives and browser backups retain dates and settings. Older client payloads
without dates continue to work. Supabase already stores alert lines as JSON;
this release requires no SQL or environment changes. Already installed APKs
receive this feature only after installing the new APK.

## Review and checks

The affected flow is reviewed on native Kivy and Chromium/WebKit at phone sizes:
upfront default, invalid/valid custom dates, mini chart/readout, explicit-only
calculation, stale Save protection, Update preservation, New alerts on, Home
labels and restart persistence. Native and web retain their OS-specific date
keyboards/pickers and notification permission UI. These fixtures do not establish
physical-device keyboard, scheduling or delivery behaviour.

```sh
python -m unittest tests.test_history_window -v
python -m scripts.smoke_history_ui
npm test --prefix web
npm run build --prefix web
python -m scripts.smoke_history_web
```

The browser regression runs actual Pyodide/NumPy on both engines with intercepted
market fixtures. It blocks service workers in this test so their activation
cannot bypass the fixture routes; the separate offline smoke tests exercise
service-worker caching. No live market, email or push requests are made.
Screenshots are retained in Actions diagnostics under `history-ui/` and
`history-web/`. See [release validation status](ANDROID_TEST_STATUS.md).
