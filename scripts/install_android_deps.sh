#!/usr/bin/env bash
# Ubuntu 22.04 host dependencies for the Android GitHub Actions job.
set -euo pipefail

run_as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

android_apt_dir="$(mktemp -d)"
trap 'run_as_root rm -rf -- "$android_apt_dir"' EXIT
chmod 755 "$android_apt_dir"
mkdir -p "$android_apt_dir/lists/partial"

# Avoid the runner's mirror+file route through azure.archive.ubuntu.com.
# Fresh, scoped indexes prevent a failed update from reusing its stale lists.
# Ubuntu's installed archive keyring still verifies every repository signature.
cat > "$android_apt_dir/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu jammy-updates main restricted universe multiverse
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu jammy-backports main restricted universe multiverse
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse
SOURCES

apt_options=(
    -o "Dir::Etc::sourcelist=$android_apt_dir/sources.list"
    -o 'Dir::Etc::sourceparts=-'
    -o "Dir::State::lists=$android_apt_dir/lists"
    -o 'Acquire::Retries=3'
    -o 'Acquire::http::Timeout=20'
    -o 'Acquire::https::Timeout=20'
    -o 'APT::Update::Error-Mode=any'
)
run_as_root env DEBIAN_FRONTEND=noninteractive apt-get "${apt_options[@]}" update
run_as_root env DEBIAN_FRONTEND=noninteractive apt-get "${apt_options[@]}" install -y \
    git zip unzip build-essential autoconf automake libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev \
    libssl-dev xvfb libegl1 libgl1-mesa-dri libmtdev1 xclip
