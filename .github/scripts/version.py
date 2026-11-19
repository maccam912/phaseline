"""Stamp the disposable build checkout with a version derived from the workflow run."""

import os
from pathlib import Path
import re


def stamp(path, fields):
    text = path.read_text()
    for key, value in fields.items():
        literal = str(value) if isinstance(value, int) else f'"{value}"'
        text, count = re.subn(rf'^{re.escape(key)}=(?:"[^"]*"|\d+)$', f'{key}={literal}', text, flags=re.M)
        if count != 1:
            raise ValueError(f"Expected one {key} field in {path}, found {count}")
    path.write_text(text)


project = Path("project.godot")
series = re.search(r'^config/version="(\d+\.\d+)"$', project.read_text(), re.M)
if not series:
    raise ValueError("project.godot needs a major.minor config/version")
number = int(os.environ["GITHUB_RUN_NUMBER"])
version = f"{series[1]}.{number}"
stamp(project, {"config/version": version})
stamp(Path("export_presets.cfg"), {
    "application/short_version": version,
    "application/version": str(number),
    "application/file_version": f"{version}.0",
    "application/product_version": f"{version}.0",
    "version/code": number,
    "version/name": version,
})
with open(os.environ["GITHUB_OUTPUT"], "a") as output:
    print(f"version={version}", file=output)
print(f"Building Phaseline v{version}")
