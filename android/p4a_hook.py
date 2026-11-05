"""Supported p4a hook: declare WorkManager's data-sync foreground service type."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID="http://schemas.android.com/apk/res/android"
ET.register_namespace("android",ANDROID)


def after_apk_build(toolchain):
    directory=Path(toolchain._dist.dist_dir)
    path=directory/"src/main/AndroidManifest.xml"
    tree=ET.parse(path)
    application=tree.getroot().find("application")
    if application is None:
        raise ValueError("Generated Android manifest has no application")
    definition=ET.parse(Path(__file__).with_name("notification_manifest.xml")).getroot()
    name=definition.attrib[f"{{{ANDROID}}}name"]
    existing=next((node for node in application.findall("service") if node.get(f"{{{ANDROID}}}name")==name),None)
    if existing is None:
        application.append(deepcopy(definition))
    else:
        existing.attrib.update(definition.attrib)
    tree.write(path,encoding="utf-8",xml_declaration=True)
    legacy=directory/"AndroidManifest.xml"
    if legacy.exists():
        legacy.write_bytes(path.read_bytes())
