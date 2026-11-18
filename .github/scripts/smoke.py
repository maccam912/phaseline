"""Open the release archive and boot its embedded game on the native runner."""

import hashlib
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import zipfile

packages = Path(os.environ["RUNNER_TEMP"]) / "release"
version = os.environ["RELEASE_VERSION"]
platform_name, relative_program = {
    "darwin": ("macOS-universal", "Phaseline.app/Contents/MacOS/Phaseline"),
    "win32": ("Windows-x86_64", "Phaseline.exe"),
    "linux": ("Linux-x86_64", "Phaseline.x86_64"),
}[sys.platform]
archive = packages / f"Phaseline-{platform_name}.zip"
sums = dict(line.split()[::-1] for line in (packages / "SHA256SUMS.txt").read_text().splitlines())
if hashlib.sha256(archive.read_bytes()).hexdigest() != sums[archive.name]:
    raise ValueError(f"Checksum mismatch for {archive.name}")

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    program = root / relative_program
    if sys.platform == "win32":
        with zipfile.ZipFile(archive) as package:
            package.extractall(root)
        product_version = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-Item .\\Phaseline.exe).VersionInfo.ProductVersion"],
            cwd=root, text=True,
        ).strip()
        if product_version != f"{version}.0":
            raise ValueError(f"Unexpected Windows product version {product_version}")
    else:
        subprocess.run(["unzip", "-q", archive, "-d", root], check=True)
        if sys.platform == "darwin":
            app = root / "Phaseline.app"
            architectures = subprocess.check_output(["lipo", "-archs", program], text=True).split()
            if set(architectures) != {"arm64", "x86_64"}:
                raise ValueError(f"Unexpected macOS architectures {architectures}")
            subprocess.run(["codesign", "--verify", "--strict", "--deep", app], check=True)
            with (app / "Contents/Info.plist").open("rb") as handle:
                metadata = plistlib.load(handle)
            if metadata["CFBundleShortVersionString"] != version:
                raise ValueError("macOS bundle version doesn't match the release")

    log = root / "startup.log"
    subprocess.run([program, "--headless", "--log-file", log, "--quit-after", "15"],
                   cwd=root, check=True, timeout=45)
    startup = log.read_text(encoding="utf-8", errors="replace")
    print(startup)
    if "Godot Engine v4.7.2" not in startup or "ERROR:" in startup:
        raise RuntimeError("The packaged game failed the startup check")
