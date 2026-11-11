# Install SMA Stock Analyzer on your own iPhone for free

This version adds an iPhone build of the same Kivy app. It uses the same real
security search, dividend-adjusted history, persistent cache, saved SMA names,
colours, charts and backtesting as Android. It targets **iOS 15 or later**.

Use your **Mac + Xcode + a free Apple Account (Personal Team)** to sign and
install it on your own iPhone. No jailbreak or public App Store listing is
needed. **Free signing normally expires after 7 days**: reconnect the phone
and press Run in the same Xcode project to renew it. Keep the same team and
bundle identifier, and keep the app installed, to retain its on-phone data.

An APK does not work on iPhone. An unsigned iPhone app also cannot be installed
by downloading it in Safari. Xcode performs the required Apple signing locally.
You do not need to give this repository your Apple password, certificates or
provisioning profiles.

## Easiest route: download the compiled Xcode kit

The [private iPhone build workflow](https://github.com/thewongphoto/SMA-indictor/actions/workflows/ios-private.yml)
compiles the native app on GitHub's Mac runner. After a **successful** run:

Use **ios-v0.13.1** for the selected app icon, 365-day frequency calculation and
the signing-kit verifier fix. The 0.13.0 log confirms the native app and kit
compiled; its final verifier still expected two background-job identifiers
instead of the four registered for closing/opening checks. Version 0.13.1
derives that check from the shared job list and retains strict verification.
The build retains the verified source caching introduced in 0.11.2. Rerunning
an old tag still uses its original code.

1. Open that run while signed in to GitHub. Under **Artifacts**, download
   **sma-iphone-xcode-kit** to your Mac and unzip it. This contains an unsigned
   device app and a small signing project; no local Python compilation is needed.
2. Install **Xcode** free from the Mac App Store. Open it once and finish its
   first-launch setup. Use an Xcode version that supports your iPhone's iOS
   version. Your Mac must support that Xcode version too.
3. Open **SMA-iPhone.xcodeproj** from the unzipped kit. Select the blue project
   in the left sidebar, then the **smaanalyzer** target.
4. Open **Signing & Capabilities**. Leave **Automatically manage signing** on.
   Add your Apple Account through **Xcode → Settings → Accounts** if needed,
   and choose your **Personal Team**. Apple handles the sign-in locally.
5. If Xcode says the bundle identifier is unavailable, change it to a unique
   value such as `com.yourname.smaanalyzer.personal`. Record the value and keep
   using it for future installs and renewals. Changing it creates a separate app.
6. Connect your iPhone by USB, unlock it and accept **Trust This Computer**.
   Select the actual iPhone as the run destination beside the **smaanalyzer**
   scheme. This kit contains a device binary; choose your phone, not a simulator.
7. If Xcode asks, enable **Settings → Privacy & Security → Developer Mode** on
   the phone and follow Apple's restart/confirmation instructions. This is
   Apple's supported development setting.
8. Click **▶ Run** in Xcode. Xcode signs and installs the compiled app with your
   Personal Team. If the phone requests developer trust, use **Settings →
   General → VPN & Device Management** and trust your own developer account.
9. The app is now on your Home Screen. You can unplug the phone and use it.
   Search needs internet; downloaded prices and saved SMAs persist across launches.

The signing project copies the compiled Kivy payload into Xcode's app target
**before** the normal CodeSign step. It preserves the bundle identifier you
choose, Xcode's generated profile and its processed Info.plist. It requests no
push-notification, iCloud or other paid-only capability.

If the workflow is still running, wait for its result. A source commit or tag
alone does not mean the native kit compiled successfully. A failed workflow
uploads **sma-iphone-build-logs**; share the first failing step/error so it can
be corrected. The installation kit is published only after the native builds
and two simulator launches pass.

## Renew the free installation each week

Keep the unzipped kit. Reconnect/unlock your phone, open the **same** project,
confirm the same Personal Team and bundle identifier, then press **Run** again.
Do this again when the profile expires. You do not need to rebuild Python or
download a new app version just to renew signing. Do not delete the installed
app to fix expiry: deletion can remove the local database and cache.

When installing a newer kit, repeat signing with the **same team and bundle ID**
to update the existing installation. Android and iPhone keep separate on-device
libraries; this release does not add cloud sync or transfer Android saves.

## Alternative: build from the repository on your Mac

Use this if you want to change source or the precompiled kit is unavailable.
Download the repository ZIP using **Code → Download ZIP**, unzip it, then open
Terminal in the extracted folder as explained in
[START_HERE_MAC.md](https://github.com/thewongphoto/SMA-indictor/blob/main/START_HERE_MAC.md).
The desktop launcher and the iPhone launcher are separate. For this full native
build, put the source in a path without spaces, such as `~/SMA-indictor`.

Install Xcode and its iOS platform first. In **Xcode → Settings → Locations**,
select that Xcode's **Command Line Tools**. Install [Homebrew](https://brew.sh)
if necessary, then run:

```sh
brew install python@3.11 autoconf automake libtool pkg-config
bash run-ios.command
```

The launcher creates `.venv-ios`, installs the pinned official `kivy-ios`
toolchain, compiles Python/Kivy/OpenSSL and generates the Xcode project. The
first build can take an hour or more; later builds reuse compiled libraries.
Before compilation, the launcher fetches and verifies pinned OpenSSL, Kivy and
Pyobjus sources over HTTPS. Its toolchain wrapper also covers temporary Kivy
version probes during build, pip and project creation. A separate verified
source cache survives later build failures in GitHub reruns. See the
[shared source policy](MOBILE_NATIVE_SOURCES.md) and
[OpenSSL provenance](IOS_NATIVE_SOURCES.md).
Leave Terminal open. Xcode opens automatically on success. Follow steps 4–8
above to sign and install. The generated project path is recorded in
`.build-ios/current-project.txt`.

For weekly renewal, reopen the existing Xcode project and Run; rerunning the
source-generation command recreates the project and requires selecting your
team again. After changing Python source, rerun `bash run-ios.command` to stage
the new source. This never deletes the phone's saved SMA database.

The iPhone app uses the portable HTTPS search/chart implementation, with no
pandas, curl_cffi or desktop helper process. TLS certificate verification stays
enabled. Bundled `tzdata` provides Singapore/exchange timezones, and iOS app
storage retains the SQLite history and saved parameters until you explicitly
clear them or delete the app.

## Notifications and background checks on iPhone

In the app, open **Settings → Test iPhone notification** and allow notifications.
This posts a local test without a price request. Foreground alerts request a
banner and sound, then remain in Notification Center. iPhone Settings, Focus,
silent mode and the user's banner/sound preferences govern what appears.
Local notifications do **not** need an APNs server or paid developer membership.

Saved enabled SMAs request native **BGTaskScheduler** checks at the same
Singapore-time targets as Android: US Tuesday–Saturday **06:30**, SGX
Monday–Friday **18:30** for closing checks. The added opening reminders target
US Monday–Friday **21:30** and SGX Monday–Friday **09:00**, fixed Singapore time.
They use the last adjusted close, with the saved SMA strictly below it; no live
price request is made. Opening jobs more than 30 minutes late are skipped and
logged. **iOS decides when, or whether, to run them**; it cannot
promise a daily alarm at those times. Background App Refresh must be enabled;
Low Power Mode, infrequent use and force-quitting can prevent checks. This
adapter uses native OS tasks, not a Kivy timer running during suspension.
Cold background launches use a separate startup path that avoids creating a
Kivy/OpenGL window; the UI starts when the app is brought to the foreground.

The shared job checks current saved switches, uses the latest eligible market
close, suppresses duplicate daily runs/signals and records requests and
notification outcomes in **Settings → Data request log**. Expired native tasks
stop before another security fetch or notification delivery. A failed/expired
slot is not silently replayed. The app imports no UI from the background job.
The Android-only **Test background notification** button is not an iPhone
BGTaskScheduler trigger; the iPhone local-notification test does not force a
background run.

## What to test on your physical iPhone

Native compilation and simulator checks run in the workflow; they do not prove
Personal Team installation, real data connectivity or sleeping-phone delivery.
Those checks remain pending until you install the kit on your own phone:

- Search `Apple`, `VOO` and `DBS`; select a match and load real history.
- Save/rename/recolour an SMA; check the centred palette, chart gestures,
  keyboard, notch and Home indicator. Relaunch and check the library/cache.
- Post the notification test while in the app; check the banner and
  Notification Center, then test with your chosen Focus settings.
- Enable a saved SMA's phone switch and Background App Refresh. After an
  eligible close, check the request log for `notification-run`,
  `notification-check`, `notification-trigger` and `notification-delivery`.
- Renew signing through Xcode without deleting the app, and confirm saved data
  remains. Preserve this exact bundle identifier for upgrades.

## Why this does not use TestFlight

The TestFlight app and accepting someone else's invitation are free. Uploading
**your own** app to TestFlight requires the paid Apple Developer Program
(usually US$99/year). A free Apple Account's Personal Team supports Xcode
installation instead. TestFlight builds last up to 90 days; free Personal Team
profiles normally last 7 days. This guide implements the free route you chose.

Official references:

- [Apple membership comparison and Personal Team limits](https://developer.apple.com/support/compare-memberships/)
- [Run an app on a connected device](https://developer.apple.com/documentation/xcode/running-your-app-in-simulator-or-on-a-device)
- [Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)
- [TestFlight](https://developer.apple.com/testflight/)
- [Official Kivy iOS toolchain](https://github.com/kivy/kivy-ios)

Yahoo data remains for private personal use; adding iPhone packaging does not
change data-distribution permissions.
