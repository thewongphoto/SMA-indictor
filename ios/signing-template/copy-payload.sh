#!/bin/bash
set -euo pipefail
payload="$SRCROOT/UnsignedApp.app"
if [ ! -x "$payload/smaanalyzer" ]; then
  echo 'The compiled iPhone app is missing. Download the complete sma-iphone-xcode-kit artifact.'
  exit 1
fi
# Keep Xcode's processed Info.plist and Personal Team profile. The final native
# CodeSign step signs this payload under the account chosen in Xcode.
/usr/bin/rsync -a --exclude /Info.plist --exclude /_CodeSignature --exclude /embedded.mobileprovision \
  "$payload/" "$TARGET_BUILD_DIR/$WRAPPER_NAME/"
