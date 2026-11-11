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
    def assert_same_png_image(self, actual, expected):
        from PIL import Image

        # Pillow wheels can use different PNG/zlib encoders on macOS and Linux.
        # Compare the rendered asset exactly, without requiring identical IDAT
        # compression or permitting changes to its dimensions/mode/pixels.
        with Image.open(actual) as actual_image, Image.open(expected) as expected_image:
            self.assertEqual(actual_image.format, "PNG")
            self.assertEqual(expected_image.format, "PNG")
            self.assertEqual(actual_image.size, expected_image.size)
            self.assertEqual(actual_image.mode, expected_image.mode)
            self.assertEqual(actual_image.tobytes(), expected_image.tobytes(),
                             "Regenerated launcher icon pixels differ from the committed asset")

    def test_buildozer_uses_the_pinned_tools_actual_icon_option_names(self):
        config = configparser.ConfigParser()
        config.read(ROOT / "buildozer.spec")
        app = config["app"]
        self.assertEqual(app["icon.filename"], "sma_analyzer/assets/app-icon.png")
        self.assertEqual(app["icon.adaptive_foreground.filename"], "sma_analyzer/assets/" + FOREGROUND)
        self.assertEqual(app["icon.adaptive_background.filename"], "sma_analyzer/assets/" + BACKGROUND)
        self.assertEqual(app["presplash.filename"], app["icon.filename"])
        self.assertEqual(app["android.presplash_color"], "#131f31")
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
    def test_reexport_matches_committed_pixels_and_never_changes_the_master(self):
        original = MASTER.read_bytes()
        with TemporaryDirectory() as directory:
            outputs = prepare_android_icons(MASTER, directory)
            for output in outputs:
                self.assert_same_png_image(output, MASTER.with_name(output.name))
        self.assertEqual(MASTER.read_bytes(), original)

    @skipUnless(importlib.util.find_spec("PIL"), "Pillow is only needed to regenerate committed launcher exports")
    def test_different_png_compression_is_accepted_for_identical_pixels(self):
        from PIL import Image

        with TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ("plain.png", "compressed.png"))
            with Image.open(MASTER.with_name(FOREGROUND)) as image:
                image.save(first, format="PNG", compress_level=0)
                image.save(second, format="PNG", compress_level=9)
            self.assertNotEqual(first.read_bytes(), second.read_bytes())
            self.assert_same_png_image(first, second)

    @skipUnless(importlib.util.find_spec("PIL"), "Pillow is only needed to regenerate committed launcher exports")
    def test_pixel_size_and_mode_changes_still_fail_icon_comparison(self):
        from PIL import Image

        with TemporaryDirectory() as directory:
            expected, actual = (Path(directory) / name for name in ("expected.png", "actual.png"))
            image = Image.new("RGB", (32, 32), NAVY)
            image.save(expected)
            different_pixel = image.copy()
            different_pixel.putpixel((16, 16), (255, 255, 255))
            variants = {"one changed pixel": different_pixel,
                        "wrong size": image.resize((31, 32)),
                        "different mode": image.convert("RGBA")}
            for name, variant in variants.items():
                with self.subTest(name=name):
                    variant.save(actual)
                    with self.assertRaises(AssertionError):
                        self.assert_same_png_image(actual, expected)

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

    @skipUnless(importlib.util.find_spec("PIL"), "Pillow is needed to inspect the shared logo colours")
    def test_turquoise_price_crosses_from_below_to_above_orange_sma(self):
        from PIL import Image
        with Image.open(MASTER) as image:
            rgb = image.convert("RGB")
            for fraction, below in ((.3, True), (.7, False)):
                x = int(rgb.width*fraction)
                price, average = [], []
                for y in range(rgb.height):
                    r, g, b = rgb.getpixel((x, y))
                    if g>120 and g>r*1.3 and b>r*1.3:
                        price.append(y)
                    if r>180 and g>90 and r>b*1.5 and g>b*1.2:
                        average.append(y)
                self.assertTrue(price and average)
                # PNG y increases downwards; compare the actual coloured paths.
                self.assertEqual(sum(price)/len(price)>sum(average)/len(average), below)
