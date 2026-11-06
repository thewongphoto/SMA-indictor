[app]
title = SMA Stock Analyzer
package.name = smaanalyzer
package.domain = org.thewongphoto
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = sma_analyzer/assets/logos/CREDITS.txt
source.exclude_dirs = tests,scripts,experiments,docs,artifacts,.venv,.venv-android,.local,.git,.github,android,bin
version = 0.10.1
# p4a installs generic modules with --no-deps; list the HTTPS dependency closure.
requirements = python3,kivy==2.3.1,pyjnius,openssl,sqlite3,certifi,requests==2.34.2,urllib3==2.8.0,idna==3.20,charset_normalizer==3.5.2,tzdata
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,POST_NOTIFICATIONS,FOREGROUND_SERVICE,FOREGROUND_SERVICE_DATA_SYNC,WAKE_LOCK,RECEIVE_BOOT_COMPLETED
android.api = 35
android.minapi = 26
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True
# GmailAuthBridge uses RevokeAccessRequest/revokeAccess, introduced in 21.4.0.
android.gradle_dependencies = com.google.android.gms:play-services-auth:21.4.0,androidx.work:work-runtime:2.10.1
android.add_src = android/src
android.add_resources = android/res
services = Smaalerts:service/alerts.py
p4a.hook = android/p4a_hook.py
android.debug_artifact = apk
p4a.branch = v2026.05.09

[buildozer]
log_level = 2
warn_on_root = 1
