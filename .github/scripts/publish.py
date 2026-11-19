"""Publish verified builds together. A rerun can resume its own draft."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

repo = os.environ["GITHUB_REPOSITORY"]
sha = os.environ["GITHUB_SHA"]
run = os.environ["GITHUB_RUN_ID"]
version = os.environ["RELEASE_VERSION"]
tag = f"v{version}"
marker = f"<!-- phaseline-release run={run} commit={sha} -->"
directory = Path(os.environ["RUNNER_TEMP"]) / "release"
archives = ["Phaseline-macOS-universal.zip", "Phaseline-Windows-x86_64.zip", "Phaseline-Linux-x86_64.zip"]
android = "Phaseline-Android.apk"
if os.environ["CI_SIGNED_ANDROID"] == "true":
    archives.append(android)
names = {*archives, "SHA256SUMS.txt"}


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True).strip()


def api(path, *args):
    return json.loads(gh("api", f"repos/{repo}/{path}", *args))


def asset_hashes(release):
    return {asset["name"]: asset.get("digest") for asset in release["assets"] if asset["state"] == "uploaded"}


if os.environ["GITHUB_REF"] != "refs/heads/main":
    raise ValueError("Releases must target main")
if {p.name for p in directory.iterdir()} != names:
    raise ValueError(f"Expected the verified release packages {sorted(names)}")
local = {name: "sha256:" + hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}
manifest = dict(line.split()[::-1] for line in (directory / "SHA256SUMS.txt").read_text().splitlines())
if {name: local[name][7:] for name in archives} != manifest:
    raise ValueError("The release packages differ from the build manifest")

releases = [release for page in api("releases?per_page=100", "--paginate", "--slurp") for release in page]
release = next((item for item in releases if item["tag_name"] == tag), None)
refs = api(f"git/matching-refs/tags/{tag}")
ref = next((item for item in refs if item["ref"] == f"refs/tags/{tag}"), None)
if ref and (not release or ref["object"]["sha"] != sha):
    raise ValueError(f"Tag {tag} already exists outside this release run")

if release:
    if marker not in (release["body"] or "") or release["target_commitish"] != sha:
        raise ValueError(f"Existing release {tag} belongs to another run or commit")
    if not release["draft"]:
        # A maintainer may have added the locally signed APK after a successful release.
        if not ref or set(asset_hashes(release)) not in (names, names | {android}):
            raise ValueError(f"Published release {tag} has incomplete assets or tag")
        print(f"Already published {release['html_url']}")
        raise SystemExit(0)
else:
    notes = Path(os.environ["RUNNER_TEMP"]) / "release-notes.md"
    notes.write_text(
        f"Download the ZIP for your desktop and extract it to play Phaseline. "
        "The macOS package supports Apple Silicon and Intel. The Windows and Linux packages support x86-64.\n\n"
        "For Android 7.0 or later, the signed download is `Phaseline-Android.apk`. "
        "The APK includes ARM64, ARMv7, and x86-64 builds.\n\n"
        f"Built from commit `{sha}`. Checksums are in `SHA256SUMS.txt`.\n\n{marker}\n"
    )
    gh("release", "create", tag, "--repo", repo, "--draft", "--target", sha,
       "--title", f"Phaseline {tag}", "--notes-file", str(notes))

gh("release", "upload", tag, "--repo", repo, "--clobber", *[str(directory / name) for name in sorted(names)])
release_id = gh("release", "view", tag, "--repo", repo, "--json", "databaseId", "--jq", ".databaseId")
draft = api(f"releases/{release_id}")
if not draft["draft"] or marker not in draft["body"] or asset_hashes(draft) != local:
    raise ValueError("GitHub's staged release assets do not match the verified build")

# An old failure can be retried after a newer version ships. Keep that newer release marked latest.
def numeric_version(name):
    if re.fullmatch(r"v\d+\.\d+\.\d+", name):
        return tuple(map(int, name[1:].split(".")))
    return ()


latest = not any(not r["draft"] and not r["prerelease"] and numeric_version(r["tag_name"]) > numeric_version(tag)
                 for r in releases)
published = api(f"releases/{release_id}", "--method", "PATCH", "-F", "draft=false",
                "-f", f"make_latest={str(latest).lower()}")
print(f"Published {published['html_url']}")
