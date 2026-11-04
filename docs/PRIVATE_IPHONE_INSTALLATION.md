# Installing a private iPhone version

An Android **APK cannot be installed on an iPhone**. An equivalent Kivy app can
be built separately for iOS as an Apple-signed app / IPA. Jailbreaking and a
public App Store listing are not necessary for the private routes below.

This is a feasibility guide, not a completed or tested iOS build of SMA-indictor.

## Installation choices

| Route | Requirements | Practical limit |
| --- | --- | --- |
| Xcode Personal Team, for your own phone | A Mac, Xcode, Apple Account, connected/paired iPhone and device development setup, including Developer Mode where required. No paid developer membership for basic personal device testing. | Free provisioning commonly lasts **7 days**, after which the app must be rebuilt/re-signed and installed again. Limits on capabilities, devices and App IDs apply. Suitable for an initial personal test. |
| Paid Apple Developer Program, development or Ad Hoc install | A Mac/Xcode build and signing setup; register each target iPhone's device identifier and use an appropriate provisioning profile. Membership is generally **US$99/year**, with regional pricing and eligibility rules. | Ad Hoc distribution supports up to **100 registered devices per product family per membership year**. Certificates/profiles expire and must be renewed. A downloaded IPA cannot run indefinitely on arbitrary unregistered phones. No public App Store listing is required. |
| TestFlight private testing | Paid developer membership, App Store Connect upload and tester invitation. | Each build lasts **90 days**. External testing can require Beta App Review. This avoids a public store listing, but does upload the build to Apple's distribution infrastructure. |

For one personal iPhone, start with Xcode development installation if weekly
re-signing is acceptable. Paid development/Ad Hoc provisioning is more practical
for ongoing personal use. If you want **no App Store Connect upload at all**,
use Xcode development or Ad Hoc, rather than TestFlight.

This does not require enterprise-distribution certificates or a jailbreak.
Region-specific alternative distribution programs are not needed for this plan.

## Work needed for this repository

1. Use **kivy-ios** to compile the required libraries and create an Xcode project.
   This needs macOS/Xcode; the existing Linux Android build job cannot produce
   a signed iOS application.
2. Reuse the Kivy screens and pure-Python calculations. Adapt Android-specific
   Pyjnius/notification/window behavior to iOS APIs or disable unsupported
   features explicitly for the first private test.
3. Verify the selected iOS Python version and native recipes for every Yahoo
   dependency. pandas, NumPy and curl_cffi need platform-compatible packaging.
   Android packaging success does not establish iOS compatibility.
4. Use iOS persistent application storage for prices, identities and saved
   parameters. Restarting the app should retain them; deleting the app may
   remove them. Export/restore is a separate backup feature.
5. Test safe areas, keyboard/search submission, scrolling, pinch/crosshair
   gestures, lifecycle transitions, offline cache use and data access on the
   actual phone. Background scheduling differs from Android and needs its own
   design if closed-app alerts are wanted.
6. Select a unique iOS bundle identifier, configure signing in Xcode, register
   the phone where needed and install via the selected route. Keep signing
   keys and Apple credentials out of GitHub.

## Official references and verification limits

The [official kivy-ios README](https://github.com/kivy/kivy-ios#readme) was read
for this assessment. It confirms the macOS/Xcode toolchain and native recipe
requirements. Apple reference pages were blocked by this cloud's network policy,
so current regional prices and account-specific provisioning conditions were
not independently retrieved during this review. Check the following before
enrolling or distributing; the figures above describe the usual program rules.

- [Apple membership comparison, including Personal Team limitations](https://developer.apple.com/support/compare-memberships/).
- [Distribution to registered devices](https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices).
- [TestFlight](https://developer.apple.com/testflight/).
- [Kivy for iOS toolchain](https://github.com/kivy/kivy-ios).

See the [Yahoo integration plan](YAHOO_FINANCE_INTEGRATION_PLAN.md) for data-source,
cache and platform dependency decisions shared with Android.
