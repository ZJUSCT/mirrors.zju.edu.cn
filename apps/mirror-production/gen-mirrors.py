#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "jinja2",
#   "pyyaml",
# ]
# ///
"""gen-mirrors.py —— 从 mirrors/ 清单生成 Mirror CR。

用法：
    ./gen-mirrors.py [输出目录]      # 默认 mirrors-generated/
    ./gen-mirrors.py --check        # 渲染到临时目录，与 mirrors-generated/ 对比

维护约定：mirrors-generated/ 完全由本脚本维护，不可手改；改 mirrors/
或 snippets/ 后重新生成并提交。特例镜像在 mirrors-manual/ 手工维护。
"""

import sys
import tempfile
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

HERE = Path(__file__).resolve().parent
KNOWN_TYPES = {"rsync", "ftpsync", "qfm", "tsumugu"}
TIERS = {"small", "standard", "hot"}
QFM_MODULES = {
    "fedora-alt",
    "fedora-archive",
    "fedora-enchilada",
    "fedora-epel",
    "fedora-secondary",
}

env = Environment(
    loader=FileSystemLoader(HERE / "snippets"),
    trim_blocks=True,
    lstrip_blocks=False,
    keep_trailing_newline=True,
)
# YAML 标量安全表示 (字符串里含 :/- 等也能正确加引号);
# 列表包装避免顶层标量被追加文档结束标记 "..."
env.filters["ys"] = lambda v: yaml.safe_dump(
    [v], allow_unicode=True, default_flow_style=True
)[1:-2].strip()


def validate(entry):
    name = entry.get("metadata", {}).get("name")
    problems = []
    if not name:
        problems.append("missing metadata.name")
        name = "??"
    for field in ("info.description", "info.upstream", "sync.type",
                  "sync.interval", "sync.timeout", "publish.http.tier"):
        node = entry
        for part in field.split("."):
            if not isinstance(node, dict) or part not in node:
                problems.append(f"missing {field}")
                break
            node = node[part]
    sync = entry.get("sync", {})
    sync_type = sync.get("type")
    if sync_type not in KNOWN_TYPES:
        problems.append(f"sync.type {sync_type!r} not in {sorted(KNOWN_TYPES)}")
    uid = sync.get("uid", 65432 if sync_type == "qfm" else 65532)
    if type(uid) is not int or not 0 < uid < 4294967295:
        problems.append("sync.uid must be a non-zero numeric UID")
    if sync_type == "tsumugu":
        upstream = entry.get("info", {}).get("upstream", "")
        if not upstream.startswith(("http://", "https://")):
            problems.append("tsumugu upstream must be an HTTP(S) URL")
        options = sync.get("tsumugu", {})
        for field, default, minimum in [("threads", 4, 1), ("max_delete", 100, 0)]:
            value = options.get(field, default)
            if type(value) is not int or value < minimum:
                problems.append(f"sync.tsumugu.{field} must be an integer >= {minimum}")
        if not isinstance(options.get("extra_args", []), list) or not all(
            isinstance(arg, str) for arg in options.get("extra_args", [])
        ):
            problems.append("sync.tsumugu.extra_args must be a list of strings")
    node_selector = sync.get("nodeSelector")
    if node_selector is not None and (
        not isinstance(node_selector, dict)
        or not node_selector
        or not all(isinstance(k, str) and isinstance(v, str)
                   for k, v in node_selector.items())
    ):
        problems.append("sync.nodeSelector must be a non-empty string mapping")
    if sync_type == "qfm":
        module = sync.get("qfm", {}).get("module")
        if module not in QFM_MODULES:
            problems.append(
                f"sync.qfm.module {module!r} not in {sorted(QFM_MODULES)}"
            )
        upstream = entry.get("info", {}).get("upstream", "")
        if upstream.startswith("rsync://"):
            _, _, upstream_path = upstream[len("rsync://"):].rstrip("/").partition("/")
            if module in QFM_MODULES and upstream_path != module:
                problems.append(
                    f"info.upstream module {upstream_path!r} does not match "
                    f"sync.qfm.module {module!r}"
                )
    if entry.get("publish", {}).get("http", {}).get("tier") not in TIERS:
        problems.append(f"publish.http.tier not in {sorted(TIERS)}")
    for i, alias in enumerate(entry.get("publish", {}).get("aliases", [])):
        where = f"publish.aliases[{i}]"
        if isinstance(alias, str):
            alias = {"path": alias}
        if not isinstance(alias, dict) or not alias.get("path"):
            problems.append(f"{where} must be a path string or a mapping with path")
            continue
        path = alias["path"]
        if (
            not path.startswith("/")
            or path.endswith("/")
            or "//" in path
            or any(ch.isspace() for ch in path)
        ):
            problems.append(f"{where}.path {path!r} is not a valid public path")
        subset = alias.get("subset")
        if subset is None:
            continue
        subpath = subset.get("subpath", "") if isinstance(subset, dict) else ""
        if (
            not isinstance(subset, dict)
            or not subpath
            or subpath.startswith("/")
            or subpath.endswith("/")
            or "//" in subpath
            or any(ch.isspace() for ch in subpath)
            or any(seg in (".", "..") for seg in subpath.split("/"))
        ):
            problems.append(
                f"{where}.subset.subpath must be a non-empty relative path of plain segments"
            )
    if not entry.get("storage", {}).get("size"):
        problems.append("missing storage.size")
    publish_subpath = entry.get("publish", {}).get("http", {}).get("subPath")
    if publish_subpath is not None and (
        not isinstance(publish_subpath, str)
        or not publish_subpath
        or publish_subpath.startswith("/")
        or ".." in publish_subpath.split("/")
    ):
        problems.append("publish.http.subPath must be a non-empty relative path")
    if problems:
        raise SystemExit(f"[{name}] " + "; ".join(problems))


def render(entry):
    sync = entry["sync"]
    upstream = entry["info"]["upstream"]
    host = path = ""
    if sync["type"] != "tsumugu":
        if not upstream.startswith("rsync://"):
            raise SystemExit(f"[{entry['metadata']['name']}] upstream 必须是 rsync:// URL: {upstream}")
        stripped = upstream[len("rsync://"):].rstrip("/")
        host, _, path = stripped.partition("/")
    ftpsync = sync.get("ftpsync", {})
    return env.get_template("mirror.yaml.j2").render(
        m=entry,
        sync_uid=sync.get("uid", 65432 if sync["type"] == "qfm" else 65532),
        host=host,
        path=path,
        ipv6=sync.get("ipv6", True),
        sync_rsync=sync.get("rsync", {}),
        rsync_extra_args=sync.get("rsync", {}).get("extra_args", []),
        ftpsync_extra=ftpsync.get("rsync_extra", "-6"),
    )


def render_kustomization(names):
    resources = "\n".join(f"  - {name}.yaml" for name in names)
    return (
        "apiVersion: kustomize.config.k8s.io/v1beta1\n"
        "kind: Kustomization\n"
        "resources:\n"
        f"{resources}\n"
    )


def generate(out_dir: Path, entries):
    names = []
    rendered = {}
    for entry in entries:
        validate(entry)
        name = entry["metadata"]["name"]
        if name in names:
            raise SystemExit(f"duplicate mirror: {name}")
        names.append(name)
        rendered[f"{name}.yaml"] = render(entry)

    rendered["kustomization.yaml"] = render_kustomization(sorted(names))
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in out_dir.glob("*.yaml"):
        if path.name not in rendered:
            path.unlink()
    for filename, content in rendered.items():
        (out_dir / filename).write_text(content)
    return names


def load_entries():
    entries = []
    for path in sorted((HERE / "mirrors").glob("*.yaml")):
        entry = yaml.safe_load(path.read_text())
        if not isinstance(entry, dict):
            raise SystemExit(f"{path.name} 应为单个镜像映射")
        entries.append(entry)
    if not entries:
        raise SystemExit("mirrors/ 中没有镜像配置")
    return entries


def main():
    entries = load_entries()

    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        with tempfile.TemporaryDirectory() as td:
            generated_dir = Path(td)
            names = generate(generated_dir, entries)
            changed = []
            expected = {
                path.name: path.read_text()
                for path in generated_dir.glob("*.yaml")
            }
            actual = {
                path.name: path.read_text()
                for path in (HERE / "mirrors-generated").glob("*.yaml")
            }
            for filename in expected.keys() | actual.keys():
                if expected.get(filename) != actual.get(filename):
                    changed.append(filename)
            if changed:
                print("生成物与 mirrors-generated/ 不一致（手改过生成物，或清单/模板变更未提交）：")
                for filename in sorted(changed):
                    print(f"  {filename}")
                sys.exit(1)
            print(f"OK: {len(names)} 个 Mirror CR 和 kustomization.yaml 与 mirrors-generated/ 一致")
        return

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "mirrors-generated"
    names = generate(out, entries)
    print(f"已生成 {len(names)} 个 CR 到 {out}/")


if __name__ == "__main__":
    main()
