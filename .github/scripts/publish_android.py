"""Sign the matching Actions artifact locally and attach the APK to its published release."""

import argparse
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from android_apk import APK, sign, validate


def gh(*args):
    return subprocess.check_output(["gh", *map(str, args)], text=True).strip()


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish(tag, keystore):
    password = os.environ.pop("ANDROID_KEYSTORE_PASSWORD", None)
    repo = "maccam912/phaseline"
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Expected a Phaseline version tag such as v1.1.3")
    release_path = f"repos/{repo}/releases/tags/{tag}"
    release = json.loads(gh("api", release_path))
    marker = re.search(r"<!-- phaseline-release run=(\d+) commit=([0-9a-f]{40}) -->", release["body"])
    if release["draft"] or not marker:
        raise ValueError("Expected a published release created by the Phaseline workflow")
    run_id, commit = marker.groups()
    tag_commit = json.loads(gh("api", f"repos/{repo}/git/ref/tags/{tag}"))["object"]["sha"]
    run = json.loads(gh("api", f"repos/{repo}/actions/runs/{run_id}"))
    if not (tag_commit == commit == release["target_commitish"] == run["head_sha"] and
            run["head_branch"] == "main" and run["path"] == ".github/workflows/release.yml" and
            run["conclusion"] == "success" and str(run["run_number"]) == tag.split(".")[-1]):
        raise ValueError("Release, tag and successful Actions build do not match")

    with tempfile.TemporaryDirectory() as work:
        root = Path(work)
        signed_apk = root / APK
        manifest = root / "SHA256SUMS.txt"
        assets = {item["name"]: item["digest"] for item in release["assets"]}
        # The build artifact keeps the original manifest if a previous upload was interrupted.
        if manifest.name in assets:
            gh("release", "download", tag, "--repo", repo, "--pattern", manifest.name, "--dir", root)
            if assets[manifest.name] != "sha256:" + checksum(manifest):
                raise ValueError("Downloaded checksum manifest differs from GitHub's asset digest")
        elif APK in assets:
            gh("run", "download", run_id, "--repo", repo, "--name", "release-packages", "--dir", root)
        else:
            raise ValueError("Initial release is missing its checksum manifest")
        sums = {name: value for value, name in (line.split() for line in manifest.read_text().splitlines())}
        desktop = {"Phaseline-macOS-universal.zip", "Phaseline-Windows-x86_64.zip", "Phaseline-Linux-x86_64.zip"}
        for name in desktop:
            if assets[name] != "sha256:" + sums[name]:
                raise ValueError(f"Published desktop asset differs from manifest: {name}")
        if (set(sums) - {APK}) != desktop or (set(assets) - {manifest.name, APK}) != desktop:
            raise ValueError("Unexpected release assets or checksum manifest entries")
        if APK in assets:
            gh("release", "download", tag, "--repo", repo, "--pattern", APK, "--dir", root)
            validate(signed_apk, tag[1:], signed=True)
            digest = checksum(signed_apk)
            if assets[APK] != "sha256:" + digest:
                raise ValueError("Existing APK differs from its GitHub digest")
        else:
            if APK in sums:
                raise ValueError("Manifest references a missing APK")
            unsigned = root / "unsigned"
            gh("run", "download", run_id, "--repo", repo, "--name", "android-unsigned", "--dir", unsigned)
            sign(unsigned / APK, signed_apk, keystore, tag[1:], password or getpass("Phaseline keystore password: "))
            digest = checksum(signed_apk)
            gh("release", "upload", tag, "--repo", repo, signed_apk)
        if sums.get(APK) != digest or manifest.name not in assets:
            sums[APK] = digest
            manifest.write_text("".join(f"{sums[name]}  {name}\n" for name in sorted(sums)))
            gh("release", "upload", tag, "--repo", repo, "--clobber", manifest)
        updated = json.loads(gh("api", release_path))
        digests = {item["name"]: item["digest"] for item in updated["assets"]}
        if digests.get(APK) != "sha256:" + digest or digests[manifest.name] != "sha256:" + checksum(manifest):
            raise ValueError("GitHub did not store the expected APK and checksum manifest")
        print(f"Verified signed APK and checksums at {release['html_url']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--keystore", type=Path, required=True)
    args = parser.parse_args()
    publish(args.tag, args.keystore)
