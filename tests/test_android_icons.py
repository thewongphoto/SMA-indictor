import configparser
import importlib.util
import math
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
import zlib

from scripts.prepare_android_icons import (BACKGROUND, BRIGHT_THRESHOLD, FOREGROUND,
    LAYER_SIZE, MASTER, NAVY, ROOT, SAFE_RADIUS, prepare_android_icons)


def rgb_png(path):
    """Decode the simple non-interlaced committed exports without Pillow in CI."""
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG")
    cursor, payload = 8, bytearray()
    while cursor < len(raw):
        length = struct.unpack_from(">I", raw, cursor)[0]
        kind = raw[cursor+4:cursor+8]
        value = raw[cursor+8:cursor+8+length]
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", value)
        elif kind == b"IDAT":
            payload.extend(value)
        cursor += length + 12
    if depth != 8 or color not in (2, 6) or interlace:
        raise ValueError("Icons must be 8-bit RGB/RGBA, non-interlaced PNGs")
    channels = 3 if color == 2 else 4
    decoded = zlib.decompress(payload)
    stride = width * channels
    output, previous, cursor = bytearray(), bytearray(stride), 0
    for _ in range(height):
        kind = decoded[cursor]
        row = bytearray(decoded[cursor+1:cursor+1+stride])
        cursor += stride + 1
        for i in range(stride):
            left = row[i-channels] if i >= channels else 0
            above = previous[i]
            diagonal = previous[i-channels] if i >= channels else 0
            if kind == 1:
                predictor = left
            elif kind == 2:
                predictor = above
            elif kind == 3:
                predictor = (left + above) // 2
            elif kind == 4:
                p = left + above - diagonal
                a, b, c = abs(p-left), abs(p-above), abs(p-diagonal)
                predictor = left if a <= b and a <= c else above if b <= c else diagonal
            elif kind == 0:
                predictor = 0
            else:
                raise ValueError("Unknown PNG filter")
            row[i] = (row[i] + predictor) & 255
        output.extend(row)
        previous = row
    return width, height, channels, output


class AndroidAppIconTests(TestCase):
    def test_buildozer_uses_the_pinned_tools_actual_icon_option_names(self):
        config = configparser.ConfigParser()
        config.read(ROOT / "buildozer.spec")
        app = config["app"]
        self.assertEqual(app["icon.filename"], "sma_analyzer/assets/app-icon.png")
        self.assertEqual(app["icon.adaptive_foreground.filename"], "sma_analyzer/assets/" + FOREGROUND)
        self.assertEqual(app["icon.adaptive_background.filename"], "sma_analyzer/assets/" + BACKGROUND)
        for name in ("icon.filename", "icon.adaptive_foreground.filename", "icon.adaptive_background.filename"):
            self.assertTrue((ROOT / app[name]).is_file(), name)

    def test_committed_legacy_and_adaptive_icons_are_opaque_and_mask_safe(self):
        width, height, channels, pixels = rgb_png(MASTER)
        self.assertEqual((width, height), (1024, 1024))
        if channels == 4:
            self.assertEqual(set(pixels[3::4]), {255})
        for position in (0, (width-1)*channels, (height-1)*width*channels, (height*width-1)*channels):
            self.assertLessEqual(max(abs(value-expected) for value,expected in zip(pixels[position:position+3],NAVY)),24)
        width, height, channels, pixels = rgb_png(MASTER.with_name(FOREGROUND))
        self.assertEqual((width, height, channels), (LAYER_SIZE, LAYER_SIZE, 3))
        radius, bright = 0, 0
        for index in range(0, len(pixels), channels):
            if max(pixels[index:index+3]) > BRIGHT_THRESHOLD:
                position = index // channels
                x, y = position % width + .5, position // width + .5
                radius = max(radius, math.hypot(x-width/2, y-height/2))
                bright += 1
        self.assertGreater(bright, 1000)
        self.assertLessEqual(radius, SAFE_RADIUS)
        width, height, channels, pixels = rgb_png(MASTER.with_name(BACKGROUND))
        self.assertEqual((width, height, channels), (16, 16, 3))
        self.assertEqual(pixels, bytearray(NAVY) * (width * height))

    @skipUnless(importlib.util.find_spec("PIL"), "Pillow is only needed to regenerate committed launcher exports")
    def test_reexport_is_deterministic_and_never_changes_the_master(self):
        original = MASTER.read_bytes()
        with TemporaryDirectory() as directory:
            outputs = prepare_android_icons(MASTER, directory)
            for output in outputs:
                self.assertEqual(output.read_bytes(), MASTER.with_name(output.name).read_bytes())
        self.assertEqual(MASTER.read_bytes(), original)

    @skipUnless(importlib.util.find_spec("PIL"), "Pillow is only needed to regenerate committed launcher exports")
    def test_wrong_size_or_transparent_masters_are_rejected(self):
        from PIL import Image
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            for size, mode, color in (((100, 100), "RGB", NAVY), ((1024, 1024), "RGBA", (*NAVY, 0)),
                                      ((1024, 1024), "RGB", (255, 255, 255))):
                Image.new(mode, size, color).save(source)
                with self.assertRaises(ValueError):
                    prepare_android_icons(source, directory)
