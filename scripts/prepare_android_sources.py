"""Prime p4a's verified package cache before SDK/native compilation starts."""
import argparse
from pathlib import Path

from .native_archives import ROOT,prepare_platform_sources


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages",type=Path,default=ROOT/".buildozer/android/platform/build-arm64-v8a/packages")
    parser.add_argument("--cache",type=Path,default=ROOT/".local/native-archives")
    args=parser.parse_args()
    print("Prepared Android sources:",prepare_platform_sources("android",args.packages,args.cache))
