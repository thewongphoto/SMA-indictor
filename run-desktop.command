#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"

if command -v python3.12 >/dev/null 2>&1; then
    preview_python=python3.12
else
    preview_python=python3
fi
"$preview_python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Please use Python 3.12 for this preview."'
if [ ! -x .venv/bin/python ]; then
    "$preview_python" -m venv .venv
fi
export KIVY_HOME="${KIVY_HOME:-$PWD/.local/kivy}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PWD/.local/cache}"
export SMA_DATA_SOURCE="${SMA_DATA_SOURCE:-yahoo}"
if [ "$SMA_DATA_SOURCE" = "preview" ]; then
    export SMA_ANALYZER_DATA_DIR="${SMA_ANALYZER_DATA_DIR:-$PWD/.local/preview-data}"
else
    export SMA_ANALYZER_DATA_DIR="${SMA_ANALYZER_DATA_DIR:-$(.venv/bin/python -m sma_analyzer.paths)}"
fi
# Preserve the previous folder-local preview saves on the first persistent launch.
.venv/bin/python - <<'PY'
from pathlib import Path
import os
import shutil
old = Path(".local/preview-data")
destination = Path(os.environ["SMA_ANALYZER_DATA_DIR"])
if old.is_dir() and not destination.exists():
    shutil.copytree(old, destination)
    print("Copied earlier preview saves into persistent application storage.")
PY
mkdir -p "$KIVY_HOME" "$XDG_CACHE_HOME" "$SMA_ANALYZER_DATA_DIR" .local/cache/pip
PIP_CACHE_DIR="$PWD/.local/cache/pip" PIP_DISABLE_PIP_VERSION_CHECK=1 .venv/bin/python -m pip install -r requirements-desktop.txt

if [ "${1:-}" = "--smoke-test" ]; then
    shift
    exec .venv/bin/python -m scripts.smoke_ui "$@"
fi
exec .venv/bin/python main.py
