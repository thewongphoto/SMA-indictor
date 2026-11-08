"""Shared desktop, Android and iPhone entry point."""
import os


def run():
    if os.environ.get("KIVY_BUILD") == "ios":
        # A cold BGTask launch must not initialize SDL/OpenGL in the background.
        from sma_analyzer.ios_runtime import wait_for_foreground
        wait_for_foreground()
    from sma_analyzer.app import SMAStockAnalyzerApp
    SMAStockAnalyzerApp().run()

if __name__ == "__main__":
    run()
