# iPhone web app (Vercel): implementation guidance

## Current state

There is **no web implementation in the repository** (checked at commit 58a1816 on main). No `package.json`, web framework, manifest or service worker exists. `docs/PRIVATE_IPHONE_INSTALLATION.md` is the plan: a Next.js frontend in a new `web/` folder, a server-side API, PostgreSQL storage and an authenticated Python worker that reuses `engine.py`, `policy.py`, `backtest.py`, `schedule.py` and `notifications.py`. This handover follows that plan and adds no code.

Native iOS builds and releases stay paused.

## Layout

- Design width 360; layouts must work from 320 to 430 wide. Content max width 480, centred on larger screens.
- `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`.
- Screen height: `min-height: 100dvh`. Never `100vh` (Safari's toolbars make it too tall).
- One scroll area per screen (the content between header and tab bar). The header and tab bar stay fixed.
- Safe areas: header top padding `max(16px, env(safe-area-inset-top))`; tab bar bottom padding `max(10px, env(safe-area-inset-bottom))`; sheets add the bottom inset; left/right insets in landscape.
- Under 360 wide: side padding 14, list logos 32, shorter header actions (screen 16).

## Touch targets and scrolling

- Every tappable element at least 44 × 44, including tab items (make the whole tab cell tappable).
- No hover-only behaviour; pressed states use `surface.hover` / `accent.hover`.
- Sheets and the overlay use `overscroll-behavior: contain` so the page behind does not scroll.
- Disable pull-to-refresh conflicts on the chart only, not the whole page.

## Keyboard

- Inputs 16 px or larger (prevents focus zoom).
- Search: `type="search"`, `enterkeyhint="search"`, submit on Enter and on the Search button only.
- Email: `type="email"`, `autocomplete="email"`, `inputmode="email"`.
- Use the `visualViewport` resize event to keep the focused field and its button above the keyboard. Hide the tab bar while a text field is focused (screen 15).

## Chart gestures

- Chart element: `touch-action: none`. Two-finger pinch zooms the time range; one-finger press-and-drag shows the end-of-day inspector; double-tap or a "Zoom out" button resets.
- Vertical page scroll must still work when a single finger moves mostly vertically outside the chart.
- Keep a 16 px margin from the left edge so Safari's back swipe works in a tab.

## Safari tab versus Home Screen

| | Safari tab | Home Screen app |
| --- | --- | --- |
| Screen space | Reduced by Safari's address bar and toolbar | Full screen; status bar overlays the top |
| Navigation | Browser Back and edge swipe also work | Only in-app Back; must exist on every pushed screen |
| Notifications | Not available; show the Add to Home Screen tip | Available on iOS 16.4+ after a tap on "Enable notifications" |
| Detect | `matchMedia('(display-mode: standalone)')` or `navigator.standalone` | Same |

Required files: a web manifest (name, `start_url`, `scope`, `display: standalone`, `theme_color` and `background_color` #0B1116, 192 and 512 px icons from `assets/app-icon.png`), an Apple touch icon, and `/sw.js`.

## Notifications, background, storage, offline

- **Alerts**: a server scheduler runs the existing SGT schedules (US closing Tue–Sat 06:30, SGX closing Mon–Fri 18:30, US opening Mon–Fri 21:30, SGX opening Mon–Fri 09:00) and sends Web Push. Reuse the same rules and notification wording as Android. Preview deployments must not send real alerts.
- **Permission**: only from a tap on "Enable notifications". Handle denied and expired subscriptions; show a denied state (not designed yet).
- **Storage**: IndexedDB for cache and preferences; server for saved lines. Ask for persistent storage where supported but do not promise it. Provide export and import in Settings.
- **Offline**: the service worker caches the app shell and static assets only. Do not cache authenticated API responses. Show screen 13's banner when offline.

## Developer contact email

When a user submits or changes their email (screens 04 and 06), both apps must notify the developer by email.

- Add one server endpoint, for example `POST /api/contact-email` in the Vercel app, which sends the message through a transactional email provider. Both the Android APK and the web app call it.
- Never put email or SMTP credentials in the APK or in browser code. Keep the provider key in a server-only environment variable.
- Payload: email, previous email (for changes), a random install ID generated on first launch, platform (android / ios-web), app version, timestamp. No other personal data.
- If offline, queue the request and retry once connected; show "Saved. It will be sent when you are online." in that case.
- Add rate limiting and basic abuse protection (for example, a per-install limit).
- This is separate from the retired email-alert channel in `notifications.py` (`NotificationSettings.email`, which the app no longer sends to). Store the contact email under its own preference key.
- Counting downloads from emails only counts people who do not skip. See open decisions.
