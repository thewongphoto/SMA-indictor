"""Build the iPhone project on a Mac; staging/metadata also test on Linux.

Signing stays in the user's Xcode Personal Team, never in this script or Git.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys

from sma_analyzer.version import APP_VERSION
from sma_analyzer.schedule import JOB_IDS
from .prepare_ios_sources import prepare_ios_sources
from .ios_icons import ICON_NAME, install_app_icons

ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "smaanalyzer"
BUNDLE_ID = "org.thewongphoto.smaanalyzer"
MINIMUM_IOS = "15.0"
TOOLCHAIN_REVISION = "fd363d49eddb5ac06766348738bd89c7d46007f8"


def stage_app(destination, source=ROOT, smoke=False):
    """An allowlist prevents shipping local caches, tests or signing material."""
    destination, source = Path(destination), Path(source)
    if destination.resolve() == source.resolve() or source.resolve().is_relative_to(destination.resolve()):
        raise ValueError("Staging must not replace the source repository.")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    shutil.copy2(source / "main.py", destination / "main.py")
    package = destination / "sma_analyzer"
    if package.exists():
        shutil.rmtree(package)
    package.mkdir()
    for item in (source / "sma_analyzer").glob("*.py"):
        shutil.copy2(item, package / item.name)
    for item in (source / "sma_analyzer/assets").rglob("*"):
        if item.is_file() and item.suffix.lower() in (".png", ".jpg", ".kv", ".atlas", ".txt", ".ttf"):
            target = package / "assets" / item.relative_to(source / "sma_analyzer/assets")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    if smoke:
        shutil.copy2(source / "ios/simulator_check.py", destination / "simulator_check.py")
        (destination / "main.py").write_text("from simulator_check import SimulatorCheck\nSimulatorCheck().run()\n")
    elif (destination / "simulator_check.py").exists():
        (destination / "simulator_check.py").unlink()


def background_task_identifiers(bundle_id="$(PRODUCT_BUNDLE_IDENTIFIER)"):
    return [f"{bundle_id}.refresh.{job}" for job in JOB_IDS]


def configure_info(values, bundle_id=BUNDLE_ID):
    values.update({"CFBundleDisplayName":"SMA Stock Analyzer", "CFBundleIdentifier":"$(PRODUCT_BUNDLE_IDENTIFIER)",
                   "CFBundleShortVersionString":APP_VERSION, "CFBundleVersion":APP_VERSION,
                   "UILaunchStoryboardName":"Launch Screen",
                   "UIStatusBarHidden":False, "UIUserInterfaceStyle":"Dark",
                   "UISupportedInterfaceOrientations":["UIInterfaceOrientationPortrait"],
                   "UIBackgroundModes":["fetch"],
                   "BGTaskSchedulerPermittedIdentifiers":background_task_identifiers(),
                   "ITSAppUsesNonExemptEncryption":False})
    # Standard HTTPS only. No arbitrary-load or invalid-certificate exceptions.
    values.pop("NSAppTransportSecurity", None)
    return values


def project_reference_path(project, reference, source_root, seen=()):
    """Resolve a local PBX reference, including the template's group hierarchy."""
    if reference.get_id() in seen:
        return None
    path = Path(str(getattr(reference, "path", "")))
    if path.is_absolute():
        return path.resolve()
    tree = str(getattr(reference, "sourceTree", "<group>"))
    if tree == "SOURCE_ROOT":
        return (source_root / path).resolve()
    if tree != "<group>":
        return None
    parent = next((group for group in project.objects.get_objects_in_section("PBXGroup")
                   if reference.get_id() in group.children), None)
    base = (project_reference_path(project, parent, source_root, (*seen, reference.get_id()))
            if parent is not None else source_root)
    return (base / path).resolve() if base is not None else None


def configure_project(project_dir, bundle_id=BUNDLE_ID):
    from pbxproj import XcodeProject
    from pbxproj.pbxextensions.ProjectFiles import FileOptions
    project_dir = Path(project_dir)
    filename = project_dir / f"{PROJECT_NAME}.xcodeproj/project.pbxproj"
    project = XcodeProject.load(str(filename))
    catalog = install_app_icons(project_dir, ROOT / "sma_analyzer/assets/app-icon.png")
    # The official template's launch image is otherwise the Kivy logo, which
    # is independent of AppIcon. Replace it and its storyboard explicitly.
    launch_image = project_dir / "icon.png"
    shutil.copy2(ROOT / "sma_analyzer/assets/app-icon.png", launch_image)
    launch_screen = project_dir / "Storyboards/Launch Screen.storyboard"
    launch_screen.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "ios/LaunchScreen.storyboard", launch_screen)
    # The pinned template has a <group> reference at smaanalyzer/Images.xcassets.
    # Match its resolved path and resource phase, not another catalog's basename.
    resources = {project.get_object(build).fileRef
                 for phase in project.objects.get_objects_in_section("PBXResourcesBuildPhase")
                 for build in phase.files}
    for resource in (catalog, launch_image, launch_screen):
        references = {item.get_id() for item in project.objects.get_objects_in_section("PBXFileReference")
                      if project_reference_path(project, item, project_dir) == resource.resolve()}
        if not references.intersection(resources):
            # pbxproj's force=False deduplicates by basename, even for different paths.
            # The pinned pbxproj knows .xib but omits .storyboard from its
            # inference table. Give this one known resource its explicit type.
            project.add_file(str(resource), force=True,
                             file_options=FileOptions(ignore_unknown_type=resource.suffix == ".storyboard"))
        if resource.suffix == ".storyboard":
            for reference in project.objects.get_objects_in_section("PBXFileReference"):
                if project_reference_path(project, reference, project_dir) == resource.resolve():
                    reference.lastKnownFileType = "file.storyboard"
    source = project_dir / "SMAIOSBridge.m"
    shutil.copy2(ROOT / "ios/SMAIOSBridge.m", source)
    references = project.add_file(str(source), force=False)
    for item in references:
        item.add_compiler_flags("-fobjc-arc")
    privacy = project_dir / "PrivacyInfo.xcprivacy"
    shutil.copy2(ROOT / "ios/PrivacyInfo.xcprivacy", privacy)
    project.add_file(str(privacy), force=False)
    for config in project.objects.get_objects_in_section("XCBuildConfiguration"):
        settings = config.buildSettings
        for key in list(settings.get_keys()):
            if key.startswith("CODE_SIGN_") or key.startswith("PROVISIONING_PROFILE"):
                del settings[key]
        settings["CODE_SIGN_STYLE"] = "Automatic"
        settings["CODE_SIGN_IDENTITY"] = "Apple Development"
        settings["PRODUCT_BUNDLE_IDENTIFIER"] = bundle_id
        settings["IPHONEOS_DEPLOYMENT_TARGET"] = MINIMUM_IOS
        settings["TARGETED_DEVICE_FAMILY"] = "1"
        settings["ENABLE_USER_SCRIPT_SANDBOXING"] = "NO"
        settings["ENABLE_BITCODE"] = "NO"
        settings["STRIP_INSTALLED_PRODUCT"] = "NO"
        settings["ASSETCATALOG_COMPILER_APPICON_NAME"] = ICON_NAME
    project.save()
    info = project_dir / f"{PROJECT_NAME}-Info.plist"
    info.write_bytes(plistlib.dumps(configure_info(plistlib.loads(info.read_bytes()), bundle_id)))
    main = project_dir / "main.m"
    native_main=main.read_text().replace('IOS_IS_WINDOWED=False', 'IOS_IS_WINDOWED=True')
    native_main=native_main.replace('putenv("KIVY_BUILD=ios");',
                                    'putenv("KIVY_BUILD=ios");\n    putenv("KIVY_NO_ARGS=1");')
    main.write_text(native_main)
    # A shared scheme makes GUI Run and CI agree, without per-user Xcode files.
    target = project.objects.get_targets()[0]
    scheme = project_dir / f"{PROJECT_NAME}.xcodeproj/xcshareddata/xcschemes/{PROJECT_NAME}.xcscheme"
    scheme.parent.mkdir(parents=True, exist_ok=True)
    scheme.write_text(scheme_xml(target.get_id(), PROJECT_NAME))
    return filename.parent


def scheme_xml(target, project_name):
    reference = (f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" '
                 f'BuildableName="smaanalyzer.app" BlueprintName="smaanalyzer" '
                 f'ReferencedContainer="container:{project_name}.xcodeproj"/>')
    return (f'<?xml version="1.0" encoding="UTF-8"?><Scheme version="1.3">'
            f'<BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>'
            f'<BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" '
            f'buildForArchiving="YES" buildForAnalyzing="YES">{reference}</BuildActionEntry>'
            f'</BuildActionEntries></BuildAction>'
            f'<LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" '
            f'selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" '
            f'useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" '
            f'allowLocationSimulation="NO"><BuildableProductRunnable runnableDebuggingMode="0">{reference}'
            f'</BuildableProductRunnable></LaunchAction>'
            f'<ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/></Scheme>')


def run(command, cwd=ROOT):
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--simulator-smoke", action="store_true")
    parser.add_argument("--stage-only", action="store_true", help="Stage files only; does not compile an iPhone app")
    parser.add_argument("--reuse-toolchain", action="store_true", help="Regenerate a project using already compiled iOS libraries")
    parser.add_argument("--bundle-id", default=BUNDLE_ID)
    args = parser.parse_args()
    work = ROOT / ".build-ios"
    stage = work / "app"
    stage_app(stage, smoke=args.simulator_smoke)
    if args.stage_only:
        print(f"Staged source only: {stage}")
        return
    if sys.platform != "darwin":
        raise SystemExit("An iPhone binary requires macOS and full Xcode; staging alone is not a build.")
    if any(character.isspace() for character in str(work)):
        raise SystemExit("The native toolchain needs a folder without spaces. Copy the source to ~/SMA-indictor and run again.")
    if not shutil.which("toolchain"):
        raise SystemExit("Use bash run-ios.command or install requirements-ios-build.txt in a Mac virtual environment.")
    # All subcommands need the transport: recipe discovery in pip/create also
    # executes Kivy's temporary source/version probe.
    toolchain=[sys.executable,ROOT/"scripts/ios_toolchain.py"]
    compile_dir = work / "toolchain"
    compile_dir.mkdir(parents=True, exist_ok=True)
    if not args.reuse_toolchain:
        prepare_ios_sources(compile_dir/".cache")
        run([*toolchain, "build", "python3", "kivy", "--add-custom-recipe", ROOT/"ios/recipes/pyobjus"], compile_dir)
        run([*toolchain, "pip", "install", "--upgrade", "--platform", "any", "--only-binary=:all:",
             "--implementation", "py", "--python-version", "3.11", "--abi", "none",
             "-r", ROOT / "requirements-ios.txt"], compile_dir)
    elif not (compile_dir / "dist/root/python3/lib/python311.zip").is_file():
        raise SystemExit("No compiled iOS Python libraries. Run without --reuse-toolchain first.")
    project_dir = compile_dir / f"{PROJECT_NAME}-ios"
    # Recreate generated project files; cached compiled libraries are preserved.
    if project_dir.exists():
        shutil.rmtree(project_dir)
    run([*toolchain, "create", "SMAAnalyzer", stage, "--add-framework", "UserNotifications",
         "--add-framework", "BackgroundTasks"], compile_dir)
    project = configure_project(project_dir, args.bundle_id)
    (work / "current-project.txt").write_text(str(project))
    print(f"\nXcode project: {project}\nChoose your iPhone and Personal Team in Signing & Capabilities, then Run.")
    if args.open:
        run(["open", project])


if __name__ == "__main__":
    main()
