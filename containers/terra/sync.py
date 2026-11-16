"""按 Fedora 发布状态选择子仓库，交给 Terra 官方脚本同步。"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

COLLECTIONS = "https://admin.fedoraproject.org/pkgdb/api/collections/"
UPSTREAM = "rsync://repos.fyralabs.com/repo/"
TOOLS = Path("/usr/local/lib/terra")


def release_policy():
    supported, archived = set(), set()
    stable = set()
    with urlopen(COLLECTIONS, timeout=30) as response:
        collections = json.load(response)["collections"]
    if not isinstance(collections, list):
        raise ValueError("Invalid Fedora collections response")
    for release in collections:
        if release["name"] != "Fedora Linux":
            continue
        state = release["status"]
        if state not in {"Active", "Under Development", "EOL"}:
            raise ValueError(f"Unknown Fedora release state: {state}")
        if release["koji_name"] == "rawhide":
            if state == "Under Development":
                supported.add("rawhide")
            continue
        version = release["version"]
        if not isinstance(version, str) or not re.fullmatch(r"[1-9][0-9]*", version):
            raise ValueError("Invalid Fedora release version")
        if state in {"Active", "Under Development"}:
            supported.add(version)
        else:
            archived.add(version)
        if state == "Active":
            stable.add(version)
    if not stable or "rawhide" not in supported or supported & archived:
        raise ValueError("Incomplete or conflicting Fedora release metadata")
    return supported


def filter_rules(supported):
    rules = ["+ /appstream/"]
    for version in sorted(supported):
        for prefix in ("", "appstream/"):
            rules.extend(
                [
                    f"+ /{prefix}terra{version}/***",
                    f"+ /{prefix}terra{version}-*/***",
                ]
            )
    rules.append("- *")
    return "\n".join(rules) + "\n"


def main():
    supported = release_policy()
    root = Path(os.environ.get("MIRROR_DIR", "/data")).resolve(strict=True)
    print("Fedora release set: " + ", ".join(sorted(supported)), flush=True)
    with tempfile.TemporaryDirectory(prefix="terra-") as work:
        filters = Path(work) / "rsync.filter"
        filters.write_text(filter_rules(supported))
        env = os.environ.copy()
        env.update(
            RSYNC="/usr/local/bin/terra-rsync",
            PARALLEL="0",
            USE_RCLONE="0",
            SYNC_SOURCES="1",
            MIRROR_DIR=str(root),
            MIRROR_URL=UPSTREAM,
            TERRA_FILTER_FILE=str(filters),
        )
        env.pop("MIRROR_SUBDIR", None)
        # 只同步一次根目录；过滤掉的旧版本由 rsync --delete-excluded 清理。
        subprocess.run(["bash", str(TOOLS / "mirror.sh")], env=env, check=True)


if __name__ == "__main__":
    main()
