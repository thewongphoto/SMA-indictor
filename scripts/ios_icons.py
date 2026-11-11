"""Export the approved opaque icon master into an iPhone asset catalog.

Pillow is a host dependency of the pinned official kivy-ios tooling. These
deterministic size exports are packaging only; the approved design is unchanged.
"""
import json
from pathlib import Path


ICON_NAME = "AppIcon"
IPHONE_ICONS = (("20x20", "2x", 40), ("20x20", "3x", 60),
                ("29x29", "2x", 58), ("29x29", "3x", 87),
                ("40x40", "2x", 80), ("40x40", "3x", 120),
                ("60x60", "2x", 120), ("60x60", "3x", 180))


def install_app_icons(project_dir, master):
    from PIL import Image
    master, project_dir = Path(master), Path(project_dir)
    with Image.open(master) as image:
        if image.format != "PNG" or image.size != (1024, 1024):
            raise ValueError("The approved app icon must be a 1024×1024 PNG.")
        rgba = image.convert("RGBA")
        if rgba.getchannel("A").getextrema() != (255, 255):
            raise ValueError("The iPhone app icon must be fully opaque.")
        rgb = rgba.convert("RGB")
    catalog = project_dir / "smaanalyzer/Images.xcassets"
    appicon = catalog / f"{ICON_NAME}.appiconset"
    appicon.mkdir(parents=True, exist_ok=True)
    (catalog / "Contents.json").write_text(json.dumps({"info":{"version":1,"author":"xcode"}}, indent=2))
    images = []
    for size, scale, pixels in IPHONE_ICONS:
        filename = f"Icon-{pixels}.png"
        rgb.resize((pixels, pixels), Image.Resampling.LANCZOS).save(appicon / filename)
        images.append({"idiom":"iphone", "size":size, "scale":scale, "filename":filename})
    rgb.save(appicon / "Icon-1024.png")
    images.append({"idiom":"ios-marketing", "size":"1024x1024", "scale":"1x", "filename":"Icon-1024.png"})
    (appicon / "Contents.json").write_text(json.dumps({"images":images,"info":{"version":1,"author":"xcode"}}, indent=2))
    return catalog
