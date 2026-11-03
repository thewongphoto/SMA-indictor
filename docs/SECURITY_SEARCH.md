# Submit-only security search — 0.5.0 preview

This release prepares the search and selection UI **before** Twelve Data is
connected. It makes no Twelve Data calls and needs no API key. The local
catalogue contains 12 examples: the original two fictional counters plus Apple,
Microsoft, Alphabet/Google, Tesla, NVIDIA, Netflix, DBS, OCBC, UOB and Singapore
Airlines. Real company identities are search examples; their price histories
and dates are simulated.

## Use it

1. From Library choose **New analysis**, then type a partial ticker or company
   name in **Search security**.
   Matching ignores case, normalizes whitespace/full-width characters and
   supports multiple words. Examples: `app`, `AAPL`, `micro`, `DBS`, `bank`,
   `Singapore air`.
2. Press **Enter** on the keyboard or click/tap **Submit**. Typing, clearing,
   focusing and scrolling do not start a search. Blank queries make no request.
3. Each match shows its logo (or initials fallback), ticker, exchange and full
   company name. Logos are packaged with the app; displaying results makes no
   image-network requests. Credits are in `sma_analyzer/assets/logos/CREDITS.txt`.
4. Click/tap a match to request its simulated history. Search alone never loads
   history or changes the selected security. After loading, the selected-security
   button and status identify the new selection. Press **Optimize SMA** to run
   the analysis. Scenario controls still choose fictional history shapes.
5. Click **Selected security** to return focus to the search field. Saved SMAs
   for searched securities remain available under their exchange-qualified IDs,
   with the existing security-group menus and View/Hide/phone/heart controls.

## Request boundaries and error handling

`PreviewMarketDataProvider.search(query)` runs only after an explicit submit.
`PreviewMarketDataProvider.historical_data(security, scenario)` is called when a
match is selected, with the exact security identity rather than the partial
search text. Both operations run away from Kivy's UI thread. These separate
methods are the replacement points for the later live-data integration; no live
client or credentials are configured in this release.

Duplicate pending submissions of the same query are ignored. Query edits
invalidate pending responses without starting another request. Late search or
history responses cannot overwrite a newer query/selection. Empty/no-match/error
states are visible and retryable. A failed history load retains the previously
selected dataset. Loading history disables optimization until the load finishes.

The model also uses the preview provider for initial demo data, scenario changes
and saved-line restoration. Those remain local. The original six fictional
series and saved data are unchanged; searched company examples use deterministic
scaled demo series, not market prices.

## Desktop and Android

The same Kivy widgets/provider are used on both platforms. Follow
[the Mac guide](../START_HERE_MAC.md), download main, and run
`bash run-desktop.command`. APK version is **0.7.0**; its intentional
`apk-v0.7.0` release-tag push triggers the existing GitHub APK workflow.

Focused UI validation:

```sh
bash run-desktop.command --smoke-test --security-search-only
```

It verifies no requests while typing, Enter/Submit, actual result taps, logos
and fallbacks, duplicate suppression, out-of-order responses, failed history,
no-match/error recovery, narrow/wide layouts and injected Android keyboard
geometry. It does not claim a real Twelve Data response or device execution.
