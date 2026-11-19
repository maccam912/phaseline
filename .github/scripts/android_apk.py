"""Validate a Phaseline APK and optionally sign it with the release identity."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import zipfile


PACKAGE = "dev.maccam912.phaseline"
CERTIFICATE = "ae1914111274d6fb3661b16a7fd86c1c09227999b75695292a30b030dd6ce2c0"
APK = "Phaseline-Android.apk"


def build_tools():
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    directory = Path(os.environ["ANDROID_BUILD_TOOLS"]) if "ANDROID_BUILD_TOOLS" in os.environ else (
        Path(sdk or "") / "build-tools" / "35.0.1"
    )
    if not (directory / "apksigner").is_file():
        raise RuntimeError("Set ANDROID_HOME to the SDK, or ANDROID_BUILD_TOOLS to its build-tools directory")
    return directory


def validate(apk, version, signed):
    tools = build_tools()
    subprocess.run([tools / "zipalign", "-c", "-P", "16", "4", apk], check=True)
    info = subprocess.check_output([tools / "aapt", "dump", "badging", apk], text=True)
    number = int(version.rsplit(".", 1)[1])
    expected = f"package: name='{PACKAGE}' versionCode='{number}' versionName='{version}'"
    if not info.startswith(expected + " ") or "application-debuggable" in info:
        raise ValueError("Android package id, version or release build type mismatch")
    architecture_line = next(line for line in info.splitlines() if line.startswith("native-code:"))
    if set(re.findall(r"'([^']+)'", architecture_line)) != {"arm64-v8a", "armeabi-v7a", "x86_64"}:
        raise ValueError("Missing or unexpected Android architectures")
    with zipfile.ZipFile(apk) as package:
        for name in ("assets/game/play.gdc", "assets/project.binary", "assets/music/library.json", "assets/music/CREDITS.md"):
            package.getinfo(name)
    if signed:
        output = subprocess.check_output([tools / "apksigner", "verify", "--print-certs", apk], text=True)
        fingerprints = re.findall(r"^Signer #\d+ certificate SHA-256 digest: (\w+)$", output, re.M)
        if fingerprints != [CERTIFICATE]:
            raise ValueError("APK signature does not match the Phaseline release certificate")
    print(f"Verified {apk.name} version {version} ({number})")


def sign(source, output, keystore, version, password):
    validate(source, version, signed=False)
    subprocess.run([build_tools() / "apksigner", "sign", "--ks", keystore, "--ks-key-alias", "phaseline",
                    "--ks-pass", "env:ANDROID_KEYSTORE_PASSWORD", "--key-pass", "env:ANDROID_KEYSTORE_PASSWORD",
                    "--v4-signing-enabled", "false", "--out", output, source], check=True,
                   env={**os.environ, "ANDROID_KEYSTORE_PASSWORD": password})
    validate(output, version, signed=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("version")
    parser.add_argument("--sign-with", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.sign_with:
        if not args.out:
            parser.error("--out is required when signing")
        sign(args.apk, args.out, args.sign_with, args.version, os.environ.pop("ANDROID_KEYSTORE_PASSWORD"))
    else:
        validate(args.apk, args.version, signed=False)
