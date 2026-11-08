#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then
  echo 'The iPhone build needs a Mac with Xcode. See docs/PRIVATE_IPHONE_INSTALLATION.md.'
  exit 1
fi
if ! xcodebuild -version >/dev/null 2>&1; then
  echo 'Install full Xcode, open it once, install the iOS platform and select its Command Line Tools in Xcode Settings.'
  exit 1
fi
ios_python=$(command -v python3.11 || true)
if [ -z "$ios_python" ]; then
  echo 'Install Python 3.11 first: brew install python@3.11'
  exit 1
fi
for tool in autoconf automake glibtool pkg-config; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo 'Install build tools first: brew install autoconf automake libtool pkg-config'
    exit 1
  fi
done
"$ios_python" -m venv .venv-ios
export PATH="$PWD/.venv-ios/bin:$PATH"
.venv-ios/bin/python -m pip install --upgrade pip
.venv-ios/bin/python -m pip install -r requirements-ios-build.txt
.venv-ios/bin/python -m scripts.prepare_ios --open "$@"
