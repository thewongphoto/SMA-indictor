# November UI/UX implementation — 0.14.0

The owner supplied this handover and authorized code changes, GitHub publication,
an Android APK build and matching iPhone web UI. The original design-only commit
instructions in HOW_TO_COMMIT are historical reference, not the release scope.

## Implemented

| Experience | Android/Kivy | iPhone web |
| --- | --- | --- |
| Navigation | Home, Charts, Alerts, Settings; keyboard-aware bottom tabs | Same four tabs; Safari history and safe-area layout |
| Visual system | Bundled Manrope, dark surfaces, teal actions, semantic light theme | Same fonts/colours; system/light/dark themes |
| Home | Cached security groups, below-line priority, statuses, collapsed startup | Cached groups, close/change, summary, empty and offline states |
| SMA detail | Plain-language status, text Save, 4/6/12/Custom chips, retained chart gestures | Python-calculated SMA, chart inspection/pinch, range chips, text Save |
| Saved lines | Inline show/hide, combined name/12-colour editor; drawer retained as shortcut | Inline visibility and name/colour sheet |
| Backtest | Plain strategy names and correctly described random-price statistic | Same Python comparison engine; independent horizon controls |
| Alerts | Phone switch plus three signal-type switches per line (0.14.1); three global master types | Stored preferences; clear notice that server delivery is not implemented |
| Settings | Theme, optional contact, diagnostics, request log, cache controls, legal copy | Theme, optional contact, diagnostic log, export, cache clear, archive and private sign-in |
| Loading/cancel | Existing native presplash; continuous stroke animation plus Cancel during scoring | Loading/calculation overlay and Cancel; stale results ignored |
| Email | Hidden without configured HTTPS endpoint/capability | Hidden unless server SMTP capability is enabled |

The Python calculation, adjusted-close, calendar365, saved identity and native
notification engines are unchanged. The web worker calls those same modules;
it does not implement a second optimizer in JavaScript. The private web service
has its own persistent database; native Android storage is not synchronized.

## Resolved design conflicts

- 0.14.0 kept the existing alert model: one phone flag per line plus three global
  types. **0.14.1** adds the owner's chosen option (b): each line has its own
  switch for all three types, with the Settings switches kept as master
  switches. Upgrades default every line type On, so nothing changes until the
  user turns one Off. The mockup's crosses-below toggle is still not introduced.
  Opening reminders retain the owner's previously selected **above-line** rule.
- Start security groups collapsed, sort below-line groups first, and use bundled
  company/issuer logos with an initials fallback. Home emphasizes company name.
- Preserve saved SMA periods, automatic colour allocation (including older HSV
  colours), explicit colour overrides and 60-character custom names.
- All shown market numbers come from data/engine results. Prototype prices,
  sample dates and the hard-coded 67% figure are not used in production.
- Signup is optional and conditional on server configuration, per the owner's
  explicit answer. Count voluntary signups, not total downloads. Do not claim
  an email was sent until the server confirms acceptance. No anonymous install
  tracking or email market-alert integration is added.
- A light palette is an implementation adaptation because only dark mockups
  were supplied. Android System follows its native UI mode; desktop System
  falls back to dark. Web System follows the browser media query. Dark remains
  the native default for continuity with the approved design.
- Native chart/backtest dropdowns and the saved drawer remain available where
  existing interaction tests and dense chart controls benefit from them. The
  primary navigation and frequency selection use the new tabs/chips.
- iPhone browser notifications are not inferred from the mockups. Server Web
  Push/scheduling is still required; the UI never pretends delivery is enabled.

## Reference and runtime links

- [Original screen gallery](screens.md), including screenshots regenerated from
  the supplied standalone prototype and its interaction states.
- [Standalone design prototype](prototype/improved-screens-standalone.html)
  (download/open locally; GitHub displays HTML as source).
- [Native presentation](../../sma_analyzer/experience.py),
  [theme](../../sma_analyzer/theme.py),
  [appearance adapter](../../sma_analyzer/appearance.py).
- [Web source](../../web/README.md), [worker](../../web_worker/README.md),
  [deployment instructions](../PRIVATE_IPHONE_INSTALLATION.md).
- [Android build workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/android-debug.yml),
  [iPhone web checks](https://github.com/thewongphoto/SMA-indictor/actions/workflows/web.yml).

## Verification and remaining deployment work

The native suite covers existing model/transport/keyboard/gesture/motion rules,
plus four-tab navigation at 320/390 widths, theme contrast and combined editing.
The web browser suite checks private login, submit-only search, Python
calculation, persistence, colour/visibility independence, offline snapshots and
320/390/768 layouts. Captures are retained in validation artifacts. These are
fixture checks, not physical Android/iPhone acceptance tests.

Vercel still needs a connected project, private access secrets and the HTTPS
persistent worker. Optional email additionally needs SMTP configuration. The
Android signup base URL is deliberately empty until that deployment exists.
No native iOS build is released and no Play Protect clearance is claimed.
