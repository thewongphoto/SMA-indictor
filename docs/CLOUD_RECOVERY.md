# Cloud execution incident and recovery

Incident investigated 3 November 2026 (Singapore).

## Findings

The previous workspace reported observed phase `running`, connectivity `offline`,
and no explicit failure. Execution calls returned `No usable execution environment
is available` before any shell command ran. This reproduced from the phone app
and laptop web session. GitHub access could not be tested during that interval;
there was no evidence that GitHub authorization was the cause.

Old workspace ID:
`ccarenv_b64_Y2NhcmVudl8wOTk4NDdmOGM2OWM4MTkxODdjMzY2YTBkZmEzZjg5Zg`

The newly attached workspace reports `running/connected` and supports terminal
commands and authenticated Git read/write operations against the same repository.
Its ID is:
`ccarenv_b64_Y2NhcmVudl83NDk5ZWNmODExNTQ4MTkxYTY1YzQzYmMxMDhlNTZjYQ`

No retained diagnostic records were available during the failed attempts or the
current investigation. The agent cannot select the unavailable old machine for
shell inspection. Thus a stale or failed execution attachment is a plausible
explanation, not a proven internal root cause. OpenAI platform telemetry is
needed to distinguish lifecycle, routing, agent health or other service failures.

The replacement has healthy disk capacity and passes dependency compatibility
checks. Those observations do not prove the old machine had the same condition.
Nothing observed implicates the SMA application, API keys or the user's Wi-Fi.
No application command was reached during the failure.

## Recovery procedure for future sessions

1. Read the current environment context and runtime status. Use the newly
   selected available environment; never reuse an unavailable instance ID.
2. Prove execution with `pwd` and `git status --short --branch`. A running/online
   badge alone does not prove that commands can execute.
3. If provisioning is reported, use the supported environment wait tool. If
   execution remains unavailable, inspect diagnostic capture metadata. Do not
   read retained diagnostic logs without the user's authorization; they can
   contain credentials or private network details.
4. Retry after a meaningful state change. Repeated unchanged requests and
   repeated long waits do not repair a disconnected workspace. Report the
   mismatch and request platform recovery/replacement promptly.
5. Do not invent a mobile 'reattach' button or promise that refreshing the app
   will repair a server connection. Ask which interface the user has before
   giving interface-specific instructions.
6. Give Support both environment IDs, the time window, the exact execution
   error and running/connectivity observations. Ask them to inspect lifecycle,
   execution attachment and agent connection events. The user can contact
   https://help.openai.com/; the agent has no platform restart/repair control.
7. Once execution works, verify the checkout, preserve local changes, validate
   dependencies and test the specific Git operation needed. Never reset local
   work or request replacement credentials merely because the terminal failed.

## Protecting project work

Published source and mockups are recoverable from GitHub. Version releases and
APK builds use explicit `apk-v*` tags; a backup must not create such a tag or
bump the application version.

The library-first implementation was initially kept local pending UI approval.
The user has now approved source publication and an APK build as **0.7.0**;
the approved app and tests are included in the GitHub release commit and
`apk-v0.7.0` tag. This closes that implementation's local-only backup gap.
An ignored historical patch at `artifacts/unreleased-library-first.patch` was
also verified against the original working tree. **A backup on the same workspace does
not protect against losing that workspace.** A recoverable checkpoint requires
an external copy, such as a user-downloaded archive or an explicitly authorized
unreleased GitHub branch. Do not upload local-only app changes contrary to the
user's current publication boundary.

Before changing environments, inventory modified and untracked source files,
preserve them outside the environment, and include a handoff describing the
base commit, requirements, checks, files and release restrictions. A new chat
does not automatically inherit conversation context or uncommitted work.

These procedures reduce disruption and data-loss risk. Repository settings
cannot guarantee availability of the platform's execution service.
