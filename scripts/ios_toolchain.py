"""Run the official pinned CLI with a verified archive transport, in-process.

No installed toolchain files are edited. Every CLI command uses this entry,
including pip/create, whose recipe discovery may probe Kivy's source again.
"""
from pathlib import Path
import sys

if __package__ in (None,""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from scripts.native_archives import install_ios_archive_transport


def main():
    from kivy_ios.toolchain import Recipe,main as official_main
    restore=install_ios_archive_transport(Recipe,Path.cwd()/".cache")
    try:
        official_main()
    finally:
        restore()


if __name__=="__main__":
    main()
