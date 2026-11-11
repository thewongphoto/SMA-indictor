# Repository cleanup — 0.13.4

This cleanup makes the current Android/desktop app and planned iPhone web route
clear, and removes material that no longer supports them.

## Removed

- Retired Gmail send transport, Android authorization wrapper/Java bridge,
  sender-address setting and Google Play sign-in Gradle dependency.
- Tests whose only subject was that removed email implementation. Phone
  notification and legacy-database compatibility tests remain; a regression
  verifies that a retired email alert cannot dispatch or record success.
- The obsolete rotating-spinner metric and its tests. The current logo-motion
  metric is retained under scripts/loading_metrics.py with slow-clock/UI checks.
- Superseded per-version release notes, the stale progress diary and guides for
  simulation-only search, old Gmail setup and retired screen layouts.
- Unselected landing-flow/icon proposals, old screenshots and the rendering
  templates/scripts that generated those retired proposals. Current logo,
  chart-comparison, colour-picker and notification captures remain.

## Retained intentionally

- All active calculations, market providers, persistence, branding, Android
  services, signing safeguards and shared regression tests.
- Legacy SQLite fields and offline datasets: existing saves must remain readable,
  and explicit demo/fixture mode still exercises real UI regressions.
- experiments/ and its frequency-policy reference: tests import that independent
  reference. Live calculations use actual dates and 365-day annualization.
- Native iOS adapters, packaging sources and tests: distribution is paused,
  not erased. They protect the existing cross-platform contracts. No native
  iOS tag or workflow dispatch is requested by this cleanup.
- The stable iPhone guide URL, now containing the Vercel/PWA plan.
- Signing identity, package name, app databases/caches, released tags and Git
  history. Local state and secrets are never part of this cleanup.

## Current documentation

README and APP_SUMMARY now describe the active app rather than accumulating
historical instructions. docs/README.md is the index; CHANGELOG.md replaces the
scattered release diaries. Installation, testing and calculation guides have
been brought up to date. Relative document/image links are checked with:

```sh
python -m scripts.check_repository_docs
```

For future changes, update current guides in place and add a concise changelog
entry. Keep historical facts labelled and link Git history instead of retaining
obsolete setup instructions as if they were current. Native build completion
must be checked in Actions rather than inferred from a version string.
