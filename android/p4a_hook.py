"""Declare the private bound worker service in a separate p4a Python process."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID="http://schemas.android.com/apk/res/android"
TOOLS="http://schemas.android.com/tools"
ET.register_namespace("android",ANDROID)
ET.register_namespace("tools",TOOLS)


def after_apk_build(toolchain):
    directory=Path(toolchain._dist.dist_dir)
    path=directory/"src/main/AndroidManifest.xml"
    tree=ET.parse(path)
    application=tree.getroot().find("application")
    if application is None:
        raise ValueError("Generated Android manifest has no application")
    for attribute in ("debuggable","allowBackup","fullBackupContent","usesCleartextTraffic"):
        application.set(f"{{{ANDROID}}}{attribute}","false")
    # These jobs use a private bound service, never a foreground service.
    # Remove library declarations too, instead of only changing buildozer.spec.
    manifest=tree.getroot()
    for permission in ("android.permission.FOREGROUND_SERVICE","android.permission.FOREGROUND_SERVICE_DATA_SYNC"):
        node=next((item for item in manifest.findall("uses-permission")
                   if item.get(f"{{{ANDROID}}}name")==permission),None)
        if node is None:
            node=ET.SubElement(manifest,"uses-permission",{f"{{{ANDROID}}}name":permission})
        node.set(f"{{{TOOLS}}}node","remove")
    foreground_name="androidx.work.impl.foreground.SystemForegroundService"
    foreground=next((node for node in application.findall("service")
                     if node.get(f"{{{ANDROID}}}name")==foreground_name),None)
    if foreground is None:
        foreground=ET.SubElement(application,"service",{f"{{{ANDROID}}}name":foreground_name})
    foreground.set(f"{{{TOOLS}}}node","remove")
    for service in application.findall("service"):
        if service.get(f"{{{ANDROID}}}name")=="org.thewongphoto.smaanalyzer.ServiceSmaalerts":
            service.set(f"{{{ANDROID}}}exported","false")
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
