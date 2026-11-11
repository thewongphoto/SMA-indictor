"""Export Android launcher PNGs from the approved opaque 1024px logo master.

The generated PNGs are committed, so Buildozer/p4a only copies them and needs no
additional build or APK dependency. Re-export manually with a host that has
Pillow (for example .venv/bin/python -m scripts.prepare_android_icons).
This performs deterministic sizing/padding only, without changing the design.
Decoded pixels are reproducible; compressed PNG bytes can vary by host encoder.
"""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "sma_analyzer/assets/app-icon.png"
FOREGROUND = "app-icon-adaptive.png"
BACKGROUND = "app-icon-background.png"
NAVY = (19, 31, 49)
LAYER_SIZE = 1080  # 108dp at 10 pixels per dp.
SAFE_RADIUS = 330  # Android's central 66dp safe circle.
BRIGHT_THRESHOLD = 112  # Separates the approved bright mark from its navy field.


def foreground_radius(image):
    """Measure visible bright artwork, rather than the opaque navy square."""
    center_x, center_y = image.width / 2, image.height / 2
    radius = 0.0
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    for index, pixel in enumerate(pixels):
        if max(pixel[:3]) > BRIGHT_THRESHOLD:
            x, y = index % image.width, index // image.width
            radius = max(radius, math.hypot(x + .5 - center_x, y + .5 - center_y))
    if not radius:
        raise ValueError("The app icon master must contain the approved bright logo artwork.")
    return radius


def prepare_android_icons(master=MASTER, destination=None):
    from PIL import Image

    master = Path(master)
    destination = Path(destination or master.parent)
    with Image.open(master) as source:
        if source.format != "PNG" or source.size != (1024, 1024):
            raise ValueError("The shared app-icon master must be a 1024×1024 PNG.")
        if source.convert("RGBA").getchannel("A").getextrema() != (255, 255):
            raise ValueError("The shared app-icon master must have an opaque navy background.")
        image = source.convert("RGB")
    for position in ((0, 0), (0, 1023), (1023, 0), (1023, 1023)):
        if max(abs(value - expected) for value, expected in zip(image.getpixel(position), NAVY)) > 24:
            raise ValueError("The master must have navy outer corners; native platforms apply their own masks.")

    # Fit the chosen mark inside the guaranteed circular safe zone. Android
    # can mask/parallax the larger layer; it must not cut off a line or plus.
    radius = foreground_radius(image)
    side = min(864, int(image.width * (SAFE_RADIUS - 8) / radius))
    resized = image.resize((side, side), Image.Resampling.LANCZOS)
    foreground = Image.new("RGB", (LAYER_SIZE, LAYER_SIZE), NAVY)
    offset = (LAYER_SIZE - side) // 2
    foreground.paste(resized, (offset, offset))
    if foreground_radius(foreground) > SAFE_RADIUS:
        raise ValueError("The Android launcher artwork extends beyond its native-mask safe area.")
    destination.mkdir(parents=True, exist_ok=True)
    foreground.save(destination / FOREGROUND, format="PNG")
    Image.new("RGB", (16, 16), NAVY).save(destination / BACKGROUND, format="PNG")
    return destination / FOREGROUND, destination / BACKGROUND


if __name__ == "__main__":
    for output in prepare_android_icons():
        print(output)
