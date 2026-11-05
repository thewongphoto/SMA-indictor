"""Persistent, platform-neutral storage selection, also usable without Kivy."""
import os
from pathlib import Path
import sys


def data_directory():
    configured = os.environ.get("SMA_ANALYZER_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SMAStockAnalyzer"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SMAStockAnalyzer"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "SMAStockAnalyzer"


if __name__ == "__main__":
    print(data_directory())
