# Keep the same Android signing SHA-1

The SHA-1 identifies the **signing key**, not the source code or APK version.
Every update must use the original key and package `org.thewongphoto.smaanalyzer`.
No Google Cloud/OAuth setup is required. UI/Python updates retain the same signer.

The old workflow generated a new debug key whenever GitHub's cache was missing.
GitHub can evict caches, so that did not guarantee a stable identity. The updated
workflow restores a permanent **Actions secret** first, accepts the original
cached key as a migration fallback, and **never generates a replacement key**.
An absent/incorrect key stops the build with an explanation.

## One-time browser setup to preserve the existing cached key

Do this while the key from your successful build is still in GitHub's cache.
No passwords, keys or tokens need to be sent through chat. The private key is
never printed or included in the downloadable APK artifact.

1. In GitHub, open your profile picture → **Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → Generate new token**.
2. Name it **SMA signing migration**, give it a short expiry (for example seven
   days), choose your account as owner and grant access **only** to
   **SMA-indictor**. Under repository permissions set **Secrets: Read and write**
   and **Variables: Read and write**. Generate the token.
3. Copy it directly into your repository's **Settings → Secrets and variables →
   Actions → Secrets → New repository secret**, named **SIGNING_ADMIN_TOKEN**.
   Do not put the token in a repository file or message.
4. Open **Actions → Build Android test APK → Run workflow**. Choose **main** and
   check **One-time: save the existing cached key as a durable Actions secret**.
   Start the run.
5. Confirm the step **Persist the existing signing identity (one-time migration)**
   succeeds. In repository Actions settings you should now see:
   - Secret **ANDROID_DEBUG_KEYSTORE_BASE64**, containing the existing key.
   - Variable **ANDROID_SIGNING_SHA1**, containing its public fingerprint.
6. Compare `android-signing-info.txt` in the new artifact with your previous
   successful APK's artifact. The SHA-1 must match.
7. Delete **SIGNING_ADMIN_TOKEN** from repository secrets and revoke the temporary
   fine-grained token in your personal GitHub settings. Future builds use only
   the saved signing secret; leave the one-time checkbox **unchecked**.

The temporary token is needed because a workflow's default `GITHUB_TOKEN`
cannot write repository Actions secrets. Its one-time job is to securely retain
the already-used key. It is unrelated to Gmail or Google account authorization.

## Future updates

Use **Run workflow → main** normally. The durable signing secret survives cache
eviction, and the workflow verifies the fingerprint against ANDROID_SIGNING_SHA1.
Do not edit/delete these values or rotate the key for ordinary updates. Install
each APK over the existing app so its private SQLite data remains intact.

## If the original cached key is already missing

The build deliberately fails. A fingerprint alone cannot reconstruct a private
key. Restore **the original keystore** from a backup into the Actions secret
using the debug alias `androiddebugkey` and its original debug password `android`.
For an existing local backup, this Mac command copies its base64 to the clipboard:

```sh
base64 -i /path/to/original/debug.keystore | tr -d '\n' | pbcopy
```

Paste into the **ANDROID_DEBUG_KEYSTORE_BASE64** Actions secret, and set
**ANDROID_SIGNING_SHA1** under Variables to the original fingerprint. Do not
paste this clipboard content into chat or source control.

If neither the cache nor a backup exists, keeping the old SHA-1 is impossible.
Creating a new key would then require a deliberate application/data migration. Uninstalling the old app removes its private local data;
do not use uninstall/reinstall as a routine update method.

This remains a personal debug/test identity. Play Store release-key management
is separate future work. Secrets/keystores must remain outside the repository.
