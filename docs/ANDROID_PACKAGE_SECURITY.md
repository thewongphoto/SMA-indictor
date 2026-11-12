# Android package security and Play Protect

Source 0.13.6 builds a signed release APK. A package policy check verifies the
**final APK**, not just the keystore or build configuration. It does not certify
an app as malware-free or establish Google Play Protect clearance.

## Reported warning and 0.13.5 inspection

The reported device was a OnePlus 13R running Android 16. Google Play Protect
displayed **Harmful app blocked**, followed by **This app may be harmful**.
Google's [developer warning guidance](https://developers.google.com/android/play-protect/warning-dev-guidance)
classifies this separately from its unknown-app scan recommendation and
sensitive-permission installation block. The screenshot does not identify a
malware category or provide Google's detection rationale.

The audited 0.13.5 APK SHA-256 is
`c9c57a33ea9aaa18d89a23fab9e254bdea234aa9b462a957f999b110656e7555`.
The official Android SDK `apksigner` verified its APK v2 signature. Its compiled
manifest targets API 35, with minimum API 26. It has standard ZIP headers and
valid entry checksums. Its Android permissions do not include SMS, accessibility,
notification-listener, contacts, or package-install access.

The inspection found concrete distribution issues:

| Item | 0.13.5 finding | 0.13.6 enforcement |
| --- | --- | --- |
| Signing identity | Actual APK signer differed from the key verified by CI. | Explicitly bind release signing to the retained keystore; compare the final APK certificate with its fingerprint. |
| Debugging | `android:debuggable=true`. | Build the release variant and require `debuggable=false`. |
| Backups | `android:allowBackup=true`. | Set `allowBackup=false` and `fullBackupContent=false` for private app state. |
| Network policy | No explicit application cleartext setting. API 35 normally defaults to disallowing cleartext. | Explicitly require `usesCleartextTraffic=false`; market requests use HTTPS. |
| Unused permissions | Foreground-service and data-sync foreground-service permissions were declared. | Remove both permissions and the unused WorkManager foreground-service component. Jobs retain their private bound-service path. |
| Distribution gate | Build verified a keystore before Gradle used its default debug signing. | Upload an APK only after signature, manifest and archive checks pass; always retain separate diagnostics. |

The actual signer SHA-1 values were:

| Artifact | SHA-1 |
| --- | --- |
| 0.13.3 APK | `CDD6F2269216D1F60CFAFC3323ADDE9E488750FF` |
| 0.13.5 APK | `50AEB2C1D575265CAA95F9294F5CDFBC32439150` |
| Retained keystore verified by both earlier CI jobs | `923F5DE565128596873E319708E2789D914048F9` |

Gradle's default debug signing was not explicitly bound to the retained key.
The old signing report therefore did not establish which key signed the APK.
The new release workflow and post-build certificate check correct that defect.
These findings do **not** establish why Google classified 0.13.5 as harmful.

## Final package checks

`python -m scripts.verify_android_apk` uses the installed Android SDK tools and
rejects an APK if its signature fails, its certificate differs from the retained
key, its package/version is wrong, or its release flags violate the policy.
It also checks the compiled permission list, exported component protections,
private Python service declarations, ZIP integrity, and packaged Python files
for private databases, signing files and development state.

The required Android permissions are Internet, network-state access, notification
posting, wake locks and boot completion for the user-enabled WorkManager jobs.
AndroidX's app-specific receiver permission must be signature-protected.
The launcher is exported; the WorkManager job service and SDK diagnostic/profile
receivers require their Android system permissions. App-owned Python services
are explicitly private.

The **sma-android-test** artifact retains its existing download name but contains
a signed release APK, `android-signing-info.txt` and
`android-apk-verification.json`. **sma-android-diagnostics** contains the build
and test logs, including failures. The package report records
`play_protect_clearance: "not_verified"`: local checks do not query or override
Google's verdict. This remains a private distribution using the retained personal
signing identity, not Play Store certification.

## Installation and existing data

Android requires matching signing identities for in-place updates. The differing
certificates above mean 0.13.6 cannot promise an in-place update over the earlier
APKs. A fingerprint alone cannot recover an earlier build's private key. Keep
any installed app with important saved data while arranging a migration;
do not uninstall it or clear its storage as an update workaround.
The user reporting this warning confirmed there was no installed app/data to
preserve, so a new installation can use the retained identity. Future builds
must keep that identity. [Signing instructions](ANDROID_SIGNING.md).

App data remains local. Automatic Android cloud/full backup is disabled by the
package policy; desktop backup instructions are separate. Device-specific
transfer and physical Android notification behaviour require device testing.

## If Play Protect still blocks the new build

Keep Play Protect enabled. Record the exact APK version/SHA-256, signing
fingerprint, device/Android version and full warning wording. Compare the APK
hash with the verification report to identify the exact binary being reviewed.
The warning remains unresolved until the new APK is checked on the affected
device or Google returns a review outcome.

Google provides a [Play Protect appeal form](https://support.google.com/googleplay/android-developer/contact/protectappeals)
for developers who have reviewed the application and believe a classification
is incorrect. Use the precise package/build evidence; a rebuilt APK or a valid
signature alone does not establish that the earlier warning was a false positive.
