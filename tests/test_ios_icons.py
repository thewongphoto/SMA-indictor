import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,skipUnless

from scripts.ios_icons import install_app_icons


@skipUnless(importlib.util.find_spec("PIL"),"The official iOS host toolchain supplies Pillow for icon size exports")
class IOSIconTests(TestCase):
    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def test_all_iphone_and_marketing_slots_export_the_same_opaque_master(self):
        from PIL import Image
        master=self.root/"master.png"
        Image.new("RGB",(1024,1024),(19,31,49)).save(master)
        catalog=install_app_icons(self.root/"project",master)
        icons=catalog/"AppIcon.appiconset"
        entries=json.loads((icons/"Contents.json").read_text())["images"]
        self.assertEqual(len(entries),9)
        for entry in entries:
            points=float(entry["size"].split("x")[0])
            expected=int(points*int(entry["scale"][0]))
            with Image.open(icons/entry["filename"]) as image:
                self.assertEqual(image.size,(expected,expected))
                self.assertEqual(image.mode,"RGB")
                self.assertEqual(image.getpixel((expected//2,expected//2)),(19,31,49))
        self.assertTrue(any(entry["idiom"]=="ios-marketing" and entry["filename"]=="Icon-1024.png" for entry in entries))

    def test_transparent_or_incorrect_size_masters_are_rejected_before_export(self):
        from PIL import Image
        master=self.root/"master.png"
        Image.new("RGBA",(1024,1024),(19,31,49,0)).save(master)
        with self.assertRaisesRegex(ValueError,"fully opaque"):
            install_app_icons(self.root/"transparent",master)
        Image.new("RGB",(512,512),(19,31,49)).save(master)
        with self.assertRaisesRegex(ValueError,"1024"):
            install_app_icons(self.root/"small",master)
