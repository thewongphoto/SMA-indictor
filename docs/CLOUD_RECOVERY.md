# Cloud execution recovery and project backups

A cloud online badge describes environment availability; it does not prove a
terminal command, authenticated Git push or GitHub native build succeeded.
A laptop network problem and a cloud proxy/permission failure are different
conditions. Preserve the exact observed error before changing configuration.

## If execution or publication fails

1. Confirm the selected repository/environment and that its runtime is ready.
   In the terminal, check pwd, git status and the current commit/remote.
2. Check whether the command actually ran. A pending or interrupted execution
   approval is not a successful Git push, even if publishing is authorized in chat.
3. If the sandbox cannot reach the configured proxy, use the environment's
   supported execution-approval path. Do not disable TLS or invent another proxy.
4. If authentication or destination policy is rejected, fix the configured
   repository access/network policy in environment settings. Do not paste tokens
   into chat or source files.
5. Retry a non-force push of the intended commit and explicit Android tag.
   Require the remote-success result before reporting publication.
6. Open Actions for the matching tag. Source upload, native compilation and an
   installable APK are separate checkpoints. Retrying an older tag uses its old code.

Current Android fixes/features are preauthorized for publication. Native iOS
releases remain paused. [Release checklist](ANDROID_RELEASE_CHECKLIST.md).

## Back up the project and app state separately

- **Source:** commit and push completed work to GitHub. Keep a local clone or ZIP
  backup of important versions. Local-only commits are not backed up to GitHub.
- **Android application data:** install over the existing app with the same
  signing key/package. Do not uninstall or clear app storage to fix an update.
- **Desktop state:** while closed, privately copy the application's persistent
  data folder. See [the desktop guide](YAHOO_DESKTOP_TESTING.md).
- **Signing identity:** retain the durable Actions secret and a separate private
  backup of the original key. [Signing guide](ANDROID_SIGNING.md).

A source clone does not include phone databases, desktop caches, account secrets
or private signing keys. Git history retains retired documents and source; the
cleanup does not rewrite history or delete released tags.
