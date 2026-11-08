"""Exercise upstream Kivy's real temporary version probe with networking off."""
import argparse
from pathlib import Path
from unittest.mock import patch

from .native_archives import install_ios_archive_transport


def check(cache):
    from kivy_ios.toolchain import Recipe
    from kivy_ios.recipes.kivy import KivyRecipe
    restore=install_ios_archive_transport(Recipe,cache)
    try:
        denied=AssertionError("Kivy source/version probing must use the verified cache, without network calls.")
        with patch("urllib.request.urlopen",side_effect=denied),patch("scripts.source_fetch.urlopen",side_effect=denied):
            value=KivyRecipe().get_required_sdl_version()
        if value!="sdl2":
            raise RuntimeError("The pinned Kivy 2.3.1 source must select SDL2.")
        print("Actual upstream Kivy version probe passed with networking disabled: SDL2.")
    finally:
        restore()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    check(parser.parse_args().cache)
