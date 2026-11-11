# Current UI motion and notification banners

Current source: **0.13.4**. [Current captures](design/README.md) use controlled
fixtures, not physical-phone validation or real market performance.

## Navigation, sheets and editors

Pages use a short directional fade. Saved-line groups expand/collapse smoothly
on both library menus; hidden controls cannot receive touches. Settings remains
top-right. The archive, help and saved-line drawer share a bottom-sheet style.
Selectors fade briefly and Back closes them before leaving the page.

Naming uses a pencil at the right of the saved SMA name, with target/year below.
The palette immediately left of it offers twelve colours. Chosen colours/names
survive hide/show, restart, unsave/restore and refreshed market prices.

An uncached optimization shows the actual upward-crossing logo paths drawing
left to right above a dimmed background. The plus appears at the intersection;
the loop holds/fades and repeats until completion or Back/Escape cancellation.
GPU rendering uses elapsed time and explicit float uniforms. Mobile scoring
yields CPU/GIL time; stale callbacks cannot replace a newer result or overlay.
Saved/cached matches open immediately without artificial loading delays.

## Android notification presentation

Phone alerts and the manual test request a heads-up banner and sound, then stay
in the notification drawer. The app preserves explicit disabled/quiet channel
choices. Android permission, notification settings and Do Not Disturb determine
actual presentation; an accepted post does not establish that a banner was seen.

Use Settings → Test Android phone notification, then the separate
[Test background notification procedure](ANDROID_DAILY_NOTIFICATIONS.md).
The latter exercises WorkManager's bound Python-service path without requesting
prices. Neither is proof of a later market signal or exact-time execution.

## iPhone route

Native iOS distribution is paused. Its retained adapters are compatibility
fixtures, not an active release route. The [Vercel/PWA guide](PRIVATE_IPHONE_INSTALLATION.md)
describes the future browser implementation, Home Screen installation and Web
Push; it must use server-side scheduling while Safari is suspended.

## Verification

The release checklist runs offline startup/library checks, mobile transport/UI,
chart refinements, builder flow, motion, slow-clock logo/colour checks and
notification jobs. Logo checks inspect actual rendered brightness/centering,
plus timing, repeated cycles and cancellation while real scoring runs.
[Commands and physical-device checks](ANDROID_RELEASE_CHECKLIST.md).
