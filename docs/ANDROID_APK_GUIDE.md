# Build and test the Android app — beginner guide

You can build the APK through GitHub in your browser. You do not need to install
Python, Java or the Android SDK on your Mac for that route. Download the result
from **GitHub**, not from this chat.

This is a personal **debug/test APK**, not a Play Store release. The configured
phone target is **Android 8.0 or newer, 64-bit ARM**. Gmail authorization also
requires **Google Play services** and the sender's Google account on the phone.
Prices remain simulated. There is no live-stock feed or automatic daily scheduler.

## Current status — read this first

- Python alert rules, Gmail MIME/HTTPS sending and UI connections are implemented.
- Native Android permission/channel/icon/tap behavior and Google Identity
  authorization bridge are included, along with the build configuration.
- **No APK has been compiled in this workspace.** The local attempt stopped at
  missing `javac`; the SDK/NDK are also absent, and Google downloads are blocked.
- The GitHub workflow has been added but has **not been run here**. Its first
  successful run will validate the Android/Java compilation. If it fails, use
  the build log rather than expecting an APK to be present.
- No Google account has been connected or real email sent here. You must do the
  one-time Google setup and authorize your account on your own phone.

See [actual validation results](ANDROID_TEST_STATUS.md).

## Part 1 — ask GitHub to build your test APK

1. Open [your repository](https://github.com/thewongphoto/SMA-indictor) while
   signed in to GitHub. Confirm the branch is **main**.
2. Click **Actions** near the top of the repository. If GitHub asks you to enable
   Actions for your repository, enable them.
3. Select **Build Android test APK** in the left sidebar.
4. Click **Run workflow**, choose **main**, then click the green **Run workflow**
   button. If it is not visible on your phone, use Chrome's **Desktop site** view.
5. Open the new run. The first build downloads a substantial Android toolchain
   and may take tens of minutes. The workflow has a 90-minute timeout.
6. Wait for a **green check mark**. Scroll to **Artifacts** at the bottom of the
   run summary and download **sma-android-test**.
7. Extract that ZIP. It should contain an `.apk` file, `android-signing-info.txt`
   and `android-build.log`. The exact APK filename can vary.

**If the run is red or there is no APK:** the build failed. Open the failed step
and inspect `android-build.log` in the artifact. Artifacts may still contain the
log/fingerprint even when compilation failed. Share the relevant final error
text for troubleshooting; do not share Google tokens or passwords. Do not keep
changing dependency versions at random.

Workflow source: [android-debug.yml](../.github/workflows/android-debug.yml).
It runs only when you request it. GitHub plan limits/available Actions minutes
apply; the workflow does not create a paid server or sender service.

## Part 2 — install the APK on your phone

You can download the artifact directly on your Android phone using Chrome and
GitHub, then extract it with your Files app. Alternatively, download it on your
Mac and transfer the `.apk` file through your normal USB/file-sharing method.

1. On the phone, find the extracted `.apk` in **Files / Downloads**.
2. Tap it. Android may ask you to allow installation from that browser or Files
   app. Enable **Allow from this source** for the installer you are using.
3. Tap **Install**, then **Open**. Look for **SMA Stock Analyzer**.
4. The app should open at Screen 1. Optimize a mock counter to reach Results.
5. Turn the phone sideways: the app should stay in portrait orientation.

A first test build may use Kivy's default launcher icon. This does not affect
notification testing; notifications have a separate monochrome SMA chart icon.

If installation says the app is incompatible, check that the phone supports
64-bit ARM and Android 8+. If it says signatures do not match an existing app,
read the signing note below before uninstalling anything.

## Part 3 — test phone notifications before setting up Gmail

1. On Screen 1 choose **DEMO-SGX**, **Sideways**, and target **12 / year**.
2. Press **Optimize SMA**. The current fixed mock data should select **SMA 254**.
3. Press the heart to save it. The saved-lines sheet opens.
4. Turn **Push notifications On** for that line.
5. Press the bottom-right **gear** to open Settings.
6. Turn on both **Buy signal** and **Impending buy signal** under Phone notifications.
7. Press **Test Android phone notification**. On Android 13+, allow the permission
   dialog. The same action continues after permission is granted; you should not
   need to press it twice.
8. Pull down Android's notification shade. Confirm the simulated test message
   and monochrome chart icon. Tapping the notification should open the app.
9. Enter **273** in the EOD session field. Press **Preview EOD alerts**: it should
   show a Buy signal for SMA 254. Preview does not post or email anything.
10. Press **Send enabled alerts**. Check the phone notification. Pressing Send
    again for that exact alert should report **Already delivered**, not post a
    duplicate. The separate generic test button is intentionally repeatable.
11. Enter **272** and preview/send again. This close is strictly below SMA 254,
    so it should produce the **Monitor / Impending buy signal** message.

Those fixture sessions were checked against the real engine. They apply to the
specified DEMO-SGX Sideways/target-12 configuration, not every scenario or SMA.

If nothing appears, check Android **Settings → Apps → SMA Stock Analyzer →
Notifications**, including the **SMA research alerts** channel. Denying permission
or disabling the channel should produce a helpful app message. Sound/vibration
also depend on the phone's channel settings and Do Not Disturb mode.

## Part 4 — enable Google authorization for Gmail

The configured sender is **kelwong98@gmail.com**. Add/sign in to that Google
account on the test phone before connecting. The app does not ask for its password.

Google setup is separate from building the APK. You can test phone notifications
without completing this part. Button names in Google Cloud can change; look for
**Google Auth Platform / OAuth consent screen** and **Clients / Credentials**.

1. On your Mac, open [Google Cloud Console](https://console.cloud.google.com/)
   and sign in with the account you want to own the app's configuration.
2. Create a project, for example **SMA Stock Analyzer Personal**.
3. Open **APIs & Services → Library**, search for **Gmail API**, and click **Enable**.
4. Open **Google Auth Platform** (or **OAuth consent screen**). Set the app name
   and support/developer email. For an ordinary personal Google account, use an
   **External** audience and keep the app in **Testing** for this personal test.
5. Add **kelwong98@gmail.com** as a test user. Add a future dedicated sender as a
   test user before changing accounts.
6. In **Data Access / Scopes**, add only this scope:

   ```text
   https://www.googleapis.com/auth/gmail.send
   ```

   It permits sending messages without granting inbox-reading access.
7. Open **Clients / Credentials → Create OAuth client ID**. Choose **Android**.
8. Enter this exact Android package name:

   ```text
   org.thewongphoto.smaanalyzer
   ```

9. Open `android-signing-info.txt` from the **same GitHub build artifact as the
   APK you installed**. Copy its **SHA1** fingerprint, including the colons, into
   the Android client's signing-certificate field. Create/save the client.
10. Allow time for the configuration to propagate, then continue on the phone.

This native Google Identity flow identifies the Android app using its package
and certificate. It does **not** need a client-secret JSON file or a web-server
client secret in the APK. No Firebase project or `google-services.json` is used.
Do not paste OAuth credentials, passwords or access tokens into GitHub or chat.

Testing consent may show Google's unverified/test-app notice. Confirm it names
**your own project** and account. If Google/your organization blocks permission,
resolve the project's audience/test-user/scope configuration; do not request full
mailbox access to work around it. Google testing grants can expire or be revoked;
reconnect when prompted. Public distribution may require further verification.

### Keep the signing fingerprint matched to the APK

The workflow caches its debug keystore to reuse the certificate. GitHub caches
can expire or be deleted: always use the fingerprint bundled with the APK you
are testing. If the signing key changes, update/create the Android OAuth client
for that fingerprint. An APK with a different certificate cannot update the old
installation directly; uninstalling loses app-local saved lines/settings.
For longer-term use, move to a deliberately managed signing key before release.
Never commit a keystore or its password. This workflow is for personal testing.

## Part 5 — connect Gmail and send one test email

1. Open the app's Settings screen and find **Gmail sender: kelwong98@gmail.com**.
2. In **Recipient email address**, enter your own address for the first test and
   press **Save**. Sender and recipient can both be `kelwong98@gmail.com`.
3. Press **Connect Gmail**. Google's native consent should open for the configured
   sender account. Review and grant the send permission. Connecting sends no email.
4. Confirm the app reports the connected sender. Then press **Send a test email
   via Gmail**. **This button sends a real email.**
5. Check the recipient inbox/spam folder and the sender's Gmail **Sent** folder.
   The subject is **SMA Stock Analyzer · Gmail test**, and the body identifies a
   simulated test. Gmail API acceptance is not a guarantee of inbox placement.
6. For SMA emails, enable the desired Email notification types in Settings and
   **Email notifications On** on the saved line. Preview session 273 or 272 as in
   Part 3, then press **Send enabled alerts** to send the applicable email.
7. Press **Disconnect** to clear the app's in-memory token and revoke the Google
   sending grant. If revocation cannot reach Google, the app still clears its
   token and explains how to remove access in your Google Account settings.

A real send re-authorizes through Google before dispatch, normally silently after
consent. The app keeps only a short-lived access token in memory. It stores no
Gmail password, client secret or refresh token in SQLite. Google Play services
manages the account authorization. Restarting the app requires reconnecting or
reauthorizing on the next explicit send, not pasting a token.

Successful EOD sends are recorded to avoid normal duplicate sends for the same
line/type/channel/session. Failed attempts remain retryable. A timeout or a crash
after Gmail accepts a message can leave delivery uncertain: check **Sent** before
retrying. The generic Gmail test button is intentionally repeatable.

## Changing to a dedicated sender later

Edit [sma_analyzer/settings.py](../sma_analyzer/settings.py):

```python
GMAIL_SENDER_ADDRESS = "your-dedicated-account@gmail.com"
```

Add that account to the phone and to the Google project's test users as needed,
rebuild/install the APK, and authorize that account. Changing this constant does
not grant account access. Recipient addresses remain configurable in the app.
No custom domain or paid sending provider is required for this approach; Gmail
account/API sending limits still apply.

## Optional — build on your own Ubuntu machine

The GitHub route is easier on a Mac. If you prefer local builds, use Ubuntu 22.04
with Python 3.11 and JDK 17. Buildozer does not run natively on Windows; use Linux
or WSL2. These commands are for the Ubuntu environment, not your Mac Terminal:

```sh
sudo apt-get update
sudo apt-get install -y git zip unzip build-essential openjdk-17-jdk autoconf automake libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev python3.11-venv

git clone https://github.com/thewongphoto/SMA-indictor.git
cd SMA-indictor
python3.11 -m venv .venv-android
source .venv-android/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-android.txt
buildozer -v android debug
```

A private repository requires your normal GitHub authentication when cloning.
The debug APK appears in `bin/`. For a local build, obtain the matching SHA-1 with:

```sh
keytool -list -v -keystore "$HOME/.android/debug.keystore" -alias androiddebugkey -storepass android
```

Register that local fingerprint rather than the GitHub build fingerprint. Accept
Android SDK licenses when requested. If Ubuntu cannot find `python3.11-venv`, use
the GitHub workflow instead of changing your Mac's existing Python installation.

The pinned build setup is Buildozer 1.6.0, python-for-android v2026.05.09, API 35,
NDK 28c, Kivy 2.3.1 and arm64-v8a. The upstream recipe supplies the Android Python
runtime; you do not have to install that runtime on your Mac. The new p4a/NDK
release was selected for current Android toolchains, including 16 KB page support,
but this repository's native build/device compatibility is not yet verified.

## What this test build does not yet do

- It does not fetch genuine market prices or know that a market has just closed.
- It does not schedule daily work or deliver remote push while the app is closed.
  The implemented phone alerts are native **local Android notifications**, posted
  by the explicit test/send action. They may remain visible after leaving the app.
- It is not a signed Play Store release. There is no automatic updater, Android
  emulator/physical-device result, Gmail account connection or real-send result
  from this cloud session.

Complete Parts 1–3 first. Then use Parts 4–5 for Gmail. If either stage fails,
report the exact step and error message so it can be fixed without guessing.
