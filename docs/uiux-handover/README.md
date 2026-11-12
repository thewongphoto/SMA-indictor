# SMA Stock Analyzer: UI/UX handover

Design handover for the redesigned app, covering the **Android app (Python/Kivy)** and the planned **iPhone web app on Vercel** (Safari and Home Screen). These are the supplied design references. The owner subsequently authorized implementation in both apps; see [implementation decisions and verification](IMPLEMENTATION.md).

Prepared 12 Nov 2026 against `main` at commit 58a1816.

## The experience in one paragraph

A dark, fintech-style app built around one decision: is each saved security above or below its SMA lines? Home groups saved lines by security, with anything below a line sorted to the top. A text-labelled tab bar (Home, Charts, Alerts, Settings) replaces icon-only controls and bottom sheets. Status is written in plain language before numbers. Search runs only when the user presses Search, to keep market-data requests down. Users can show several saved lines on one chart, and rename and recolour each line. First launch asks for an optional email for release updates and a voluntary signup count (not a total download count).

## What's in this folder

| Path | Contents |
| --- | --- |
| [screens.md](screens.md) | Every screen and state with screenshots, status (approved or proposal) and changes from the current app |
| [screens/](screens/) | 2× PNG screenshots, 01–18, plus [screens/states/](screens/states/) for interaction states |
| [flows.md](flows.md) | Navigation and interaction flows (Mermaid diagrams) |
| [design-tokens.md](design-tokens.md) | Colours, SMA line colours, typography, spacing, touch targets, icons, motion |
| [tokens.json](tokens.json), [tokens.css](tokens.css) | The same tokens for code |
| [platform-comparison.md](platform-comparison.md) | Android versus iPhone web, screen by screen, plus web-only behaviour |
| [web-iphone.md](web-iphone.md) | Vercel/iPhone guidance: layout, safe areas, keyboard, gestures, Safari vs Home Screen, notifications, storage, offline, the contact-email endpoint |
| [kivy-implementation.md](kivy-implementation.md) | Kivy guidance and the source files each screen maps to |
| [open-decisions.md](open-decisions.md) | Unresolved decisions and missing materials |
| [UX_AUDIT.md](UX_AUDIT.md) | The UX audit the redesign responds to |
| [prototype/](prototype/) | Interactive prototype: source and a single-file standalone version |
| [assets/app-icon.png](assets/app-icon.png) | App icon used in loading and first-open screens (copied from `sma_analyzer/assets/`) |

## Approved versus proposal

- **Approved (01–11)**: reviewed and iterated with the app owner: Home, SMA detail, backtest, Alerts, Settings, startup loading, first-open email (with Skip for now), optimising, several lines, rename/recolour, search.
- **Proposal (12–18)**: added for this handover to cover empty, offline, error, keyboard, narrow-phone and iPhone web states. Not yet reviewed.
- Screen 03's alert switches and some prototype details conflict with the app's current rules; [open-decisions.md](open-decisions.md) lists them. Where the prototype and the code disagree on behaviour or limits, **the code wins**.

## Screen-by-screen changes

| # | Screen | Main change from the current app |
| --- | --- | --- |
| 01 | Home | Library becomes a security-grouped home; below-line securities first; tab bar |
| 02 | SMA detail | Plain-language status first; visible Custom segment; text Save |
| 02b | Backtest | Horizon chips; plain strategy names; one summary statistic |
| 03 | Alerts | Dedicated tab with per-line switches (model to confirm) |
| 04 | Settings | Contact email, legal disclaimer, single entry point |
| 05 | Startup | Logo-draw loading screen |
| 06 | First open | Optional email with Skip for now |
| 07 | Optimising | Visible Cancel button |
| 08 | Several lines | Multiple saved lines on one chart with show/hide |
| 09 | Edit line | Rename (60 chars) and 12-colour picker in a sheet |
| 10–11 | Search | Submit-only search; company names and logos |
| 12–18 | States, iPhone web | Proposals |

## Open the interactive prototype

GitHub shows HTML files as code, not as pages. To view the prototype:

1. Download `prototype/improved-screens-standalone.html` (use **Raw** or **Download raw file** on GitHub) and open it in a desktop browser. It is a single self-contained file. Pan and zoom the canvas; cards, switches, chips, inputs, the search, the email form and the line editor are interactive.
2. Or run the source version: from `docs/uiux-handover/prototype/` run `python3 -m http.server 8000` and open `http://localhost:8000/Improved%20Screens.dc.html`. It needs `support.js` and `../assets/app-icon.png` (both included) and loads Manrope from Google Fonts.

There is no hosted preview link. To share one, enable GitHub Pages for this branch, or host the standalone file anywhere.

The prototype is a design reference. Its HTML, inline styles and the `support.js` runtime are **not** production code; take values from [tokens.json](tokens.json) and behaviour from the docs. All prices, counts, backtest numbers and dates in it are samples.

## Shared rules (both platforms)

- Same tokens, screen structure, wording and flows on Android and iPhone web.
- Text labels on every action; status never shown by colour alone.
- Touch targets at least 44 × 44; text at least 12, inputs 16 on web.
- Search only on Search or Enter; recent items never fetch.
- Calculations, saved data, notification wording and schedules come from the existing Python code, unchanged.

Platform adaptations are in [platform-comparison.md](platform-comparison.md).

## Implementation

- **Android (Kivy)**: [kivy-implementation.md](kivy-implementation.md). A restyle and restructure of `app.py`, `navigation.py`, `widgets.py` and `chart.py` presentation; logic modules stay untouched.
- **iPhone web (Vercel)**: [web-iphone.md](web-iphone.md). Web code now lives in `web/` with `web_worker/`; follow `docs/PRIVATE_IPHONE_INSTALLATION.md` (Next.js in `web/`, server API, Python worker) and these screens.
- **Both**: the developer contact email needs one server endpoint (details in [web-iphone.md](web-iphone.md#developer-contact-email)).

## Dependencies and licences

| Item | Licence / owner | Notes |
| --- | --- | --- |
| Manrope font | SIL Open Font License 1.1 | Bundled in both apps with the SIL licence text |
| App icon | Project's own (`sma_analyzer/assets/app-icon.png`) | |
| Company logos | Third-party trademarks | Not included; placeholders only |
| `prototype/support.js` | Prototype runtime from the design tool | Only for viewing the prototype; not for production |
| Mermaid diagrams | Rendered by GitHub | |

## Unresolved

See [open-decisions.md](open-decisions.md): alert model, expanded cards on launch, names vs tickers, logo source, download counting, light theme, legal review, proposals 12–18.
