"""Restore the existing Android debug identity; never generate a replacement key.

The key lives in a GitHub Actions secret, with the original cache as a migration
fallback. Neither key bytes nor their base64 encoding are printed or uploaded.
"""
import base64
import os
from pathlib import Path
import re
import subprocess
import tempfile


def fingerprint(path):
    result = subprocess.run([
        "keytool", "-J-Duser.language=en", "-J-Duser.country=US", "-list", "-v",
        "-keystore", str(path), "-alias", "androiddebugkey", "-storepass", "android",
    ], capture_output=True, text=True)
    match = re.search(r"SHA1:\s*([0-9A-Fa-f:]+)", result.stdout)
    if result.returncode or not match:
        raise ValueError("The existing signing key could not be read with the Android debug alias/password.")
    return match.group(1).upper()


def prepare_identity(path, encoded="", expected_sha1=""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not encoded:
        if not path.is_file():
            raise ValueError(
                "Signing key unavailable. Restore ANDROID_DEBUG_KEYSTORE_BASE64 from your original "
                "key backup. The cached key is absent; refusing to generate a different SHA-1.")
        actual = fingerprint(path)
    else:
        try:
            data = base64.b64decode("".join(encoded.split()), validate=True)
        except ValueError:
            raise ValueError("ANDROID_DEBUG_KEYSTORE_BASE64 is not valid base64.") from None
        # Validate before replacing the cached key. This avoids silently rotating
        # the identity if somebody pastes the wrong keystore into the secret.
        with tempfile.NamedTemporaryFile(dir=path.parent) as temporary:
            temporary.write(data)
            temporary.flush()
            candidate = Path(temporary.name)
            actual = fingerprint(candidate)
            if path.is_file() and fingerprint(path) != actual:
                raise ValueError("The signing secret differs from the cached key. Restore the original key.")
            if expected_sha1 and actual != expected_sha1.strip().upper():
                raise ValueError("Signing SHA-1 differs from ANDROID_SIGNING_SHA1. Restore the original key.")
            path.write_bytes(data)
    if expected_sha1 and actual != expected_sha1.strip().upper():
        raise ValueError("Signing SHA-1 differs from ANDROID_SIGNING_SHA1. Restore the original key.")
    path.chmod(0o600)
    return actual


def main():
    try:
        actual = prepare_identity(Path.home()/".android/debug.keystore",
            os.environ.get("ANDROID_KEYSTORE_BASE64", ""), os.environ.get("ANDROID_EXPECTED_SHA1", ""))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from None
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    (artifacts/"android-signing-info.txt").write_text(
        f"Android package: org.thewongphoto.smaanalyzer\nSHA1: {actual}\n")
    print(f"Existing Android signing identity verified: SHA1 {actual}")


if __name__ == "__main__":
    main()
