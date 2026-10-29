#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "jinja2>=3.1,<4",
#     "pyyaml>=6,<7",
# ]
# ///
"""Build the common Kairos image and private per-node ISOs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import yaml


HERE = Path(__file__).resolve().parent
INVENTORY_PATH = HERE / "nodes.yaml"
TEMPLATE_NAME = "cloud-config.yaml.j2"
MAC_RE = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")
PRIVATE_KEY_RE = re.compile(r"(?m)^(\s*PrivateKey\s*=\s*).+$")


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command))
    return subprocess.run(command, check=True, text=True, **kwargs)


def run_private(command: list[str], secrets: list[str]) -> None:
    """Run a build command without streaming a potentially sensitive log."""
    print("+", " ".join(command))
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode == 0:
        return

    output = PRIVATE_KEY_RE.sub(r"\1<redacted>", result.stdout)
    for secret in secrets:
        if secret:
            output = output.replace(secret, "<redacted>")
    print(output, file=sys.stderr)
    raise subprocess.CalledProcessError(result.returncode, command)


def load_inventory() -> dict:
    with INVENTORY_PATH.open() as stream:
        inventory = yaml.safe_load(stream)

    required_sections = {
        "release",
        "network",
        "bond",
        "k3s",
        "ssh_authorized_keys",
        "nodes",
    }
    missing = required_sections - inventory.keys()
    if missing:
        raise ValueError(f"nodes.yaml is missing sections: {sorted(missing)}")

    nodes = inventory["nodes"]
    if len(nodes) != 5:
        raise ValueError(f"expected five mirror nodes, found {len(nodes)}")
    if sum(bool(node.get("bootstrap")) for node in nodes) > 1:
        raise ValueError("at most one node may have bootstrap: true")
    if not any(node.get("bootstrap") for node in nodes):
        print("note: no node has bootstrap: true; every ISO will join an "
              "existing cluster via --server")

    unique_fields = ("name", "hostname", "ipv4", "ipv6")
    for field in unique_fields:
        values = [node[field] for node in nodes]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate node {field} value")

    all_macs: list[str] = []
    for node in nodes:
        ipaddress.IPv4Address(node["ipv4"])
        ipaddress.IPv6Address(node["ipv6"])
        members = node["bond_members"]
        if len(members) not in (2, 4):
            raise ValueError(f"{node['hostname']}: bond must have two or four members")
        if node["bond_mac"] not in members:
            raise ValueError(f"{node['hostname']}: bond MAC is not a member MAC")
        for mac in [node["bond_mac"], *members]:
            if not MAC_RE.fullmatch(mac):
                raise ValueError(f"{node['hostname']}: invalid lowercase MAC {mac}")
        all_macs.extend(members)

    if len(all_macs) != len(set(all_macs)):
        raise ValueError("a physical bond-member MAC is assigned to multiple nodes")

    network = inventory["network"]
    ipaddress.IPv4Address(network["ipv4_gateway"])
    ipaddress.IPv6Address(network["ipv6_gateway"])
    for address in network["dns"]:
        ipaddress.ip_address(address)

    k3s = inventory["k3s"]
    token = k3s["token"]
    if not isinstance(token, str) or not token or any(character.isspace() for character in token):
        raise ValueError("K3s token must be one non-empty whitespace-free string")
    ipaddress.IPv4Address(k3s["api_vip"])
    for cidr in [*k3s["pod_cidrs"], *k3s["service_cidrs"]]:
        ipaddress.ip_network(cidr)
    for address in k3s["cluster_dns"]:
        ipaddress.ip_address(address)

    for key in inventory["ssh_authorized_keys"]:
        if not re.fullmatch(r"ssh-(?:ed25519|rsa|ecdsa-[^ ]+) [^ ]+(?: .*)?", key):
            raise ValueError("invalid OpenSSH public key in nodes.yaml")

    return inventory


def select_nodes(inventory: dict, requested: str | None, all_nodes: bool) -> list[dict]:
    if all_nodes:
        selected = inventory["nodes"]
    elif not requested:
        raise ValueError("specify a node name, --all, or --base-only")
    else:
        selected = [
            node
            for node in inventory["nodes"]
            if requested in (node["name"], node["hostname"])
        ]
        if not selected:
            raise ValueError(f"unknown node: {requested}")

    missing_targets = [node["hostname"] for node in selected if not node.get("install_device")]
    if missing_targets:
        raise ValueError(f"installation target is not recorded for: {', '.join(missing_targets)}")
    return selected


def render_config(
    inventory: dict,
    node: dict,
) -> str:
    environment = Environment(
        loader=FileSystemLoader(HERE),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    rendered = environment.get_template(TEMPLATE_NAME).render(
        node=node,
        network=inventory["network"],
        bond=inventory["bond"],
        k3s=inventory["k3s"],
        ssh_authorized_keys=inventory["ssh_authorized_keys"],
    )

    document = yaml.safe_load(rendered)
    files = [
        item
        for stage in ("rootfs.before", "initramfs", "initramfs.after")
        for step in document["stages"].get(stage, [])
        for item in step.get("files", [])
    ]
    embedded = {item["path"]: item["content"] for item in files}
    for required_path in (
        "/etc/rancher/k3s/registries.yaml",
        "/etc/rancher/k3s/config.yaml",
        "/etc/stunnel/stunnel.conf",
    ):
        if required_path not in embedded:
            raise ValueError(f"rendered cloud-config omits {required_path}")
    yaml.safe_load(embedded["/etc/rancher/k3s/registries.yaml"])
    yaml.safe_load(embedded["/etc/rancher/k3s/config.yaml"])
    return rendered


def build_base(inventory: dict) -> None:
    release = inventory["release"]
    run(
        [
            "docker",
            "build",
            "--pull=false",
            "--build-arg",
            f"KAIROS_VERSION={release['version']}",
            "--build-arg",
            f"K3S_VERSION={release['k3s_version']}",
            "--tag",
            release["base_image"],
            str(HERE),
        ]
    )
    run([str(HERE / "verify-image.sh"), release["base_image"], release["k3s_version"]])


def image_id(image: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_node(
    inventory: dict,
    node: dict,
    output_directory: Path,
) -> None:
    release = inventory["release"]
    rendered = render_config(inventory, node)

    with tempfile.TemporaryDirectory(prefix=f"kairos-{node['name']}-") as temporary:
        temporary_directory = Path(temporary)
        os.chmod(temporary_directory, 0o700)
        rendered_path = temporary_directory / "cloud-config.yaml"
        rendered_path.write_text(rendered)
        os.chmod(rendered_path, 0o600)

        run(
            [
                "docker",
                "run",
                "--rm",
                "--volume",
                f"{rendered_path}:/cloud-config.yaml:ro",
                "--entrypoint",
                "/usr/bin/kairos-agent",
                release["base_image"],
                "--strict-validation",
                "validate",
                "/cloud-config.yaml",
            ]
        )

        auroraboot_output = temporary_directory / "auroraboot"
        auroraboot_output.mkdir(mode=0o700)
        run_private(
            [
                "docker",
                "run",
                "--rm",
                "--volume",
                f"{auroraboot_output}:/output",
                "--volume",
                f"{rendered_path}:/cloud-config.yaml:ro",
                "--volume",
                "/var/run/docker.sock:/var/run/docker.sock",
                release["auroraboot_image"],
                "--set",
                f"container_image={release['base_image']}",
                "--set",
                "disable_netboot=true",
                "--set",
                "disable_http_server=true",
                "--set",
                "state_dir=/output",
                "--cloud-config",
                "/cloud-config.yaml",
            ],
            [
                inventory["k3s"]["token"],
            ],
        )
        generated_isos = list(auroraboot_output.glob("*.iso"))
        if len(generated_isos) != 1:
            raise ValueError(f"expected one generated ISO, found {len(generated_isos)}")
        output_directory.mkdir(parents=True, exist_ok=True)
        os.chmod(output_directory, 0o700)
        target = output_directory / f"kairos-{node['hostname']}-{release['version']}.iso"
        shutil.copyfile(generated_isos[0], target)
        os.chmod(target, 0o600)
        iso_digest = sha256(target)
        checksum = target.with_suffix(target.suffix + ".sha256")
        checksum.write_text(f"{iso_digest}  {target.name}\n")
        os.chmod(checksum, 0o600)
        metadata = target.with_suffix(target.suffix + ".json")
        metadata.write_text(
            json.dumps(
                {
                    "hostname": node["hostname"],
                    "release": release["version"],
                    "k3s_version": release["k3s_version"],
                    "base_image": release["base_image"],
                    "base_image_id": image_id(release["base_image"]),
                    "iso": target.name,
                    "sha256": iso_digest,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        os.chmod(metadata, 0o600)

    print(f"Built private ISO: {target}")
    print(f"SHA-256: {iso_digest}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("node", nargs="?", help="short name or FQDN of one node")
    parser.add_argument("--all", action="store_true", help="build all five node ISOs")
    parser.add_argument("--base-only", action="store_true", help="build and verify only the base image")
    parser.add_argument("--skip-base", action="store_true", help="reuse the existing local base image")
    parser.add_argument("--output-dir", type=Path, default=HERE / "dist", help="private ISO output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inventory = load_inventory()
    if args.all and args.node:
        raise ValueError("a node argument and --all are mutually exclusive")
    if args.base_only and (args.node or args.all or args.skip_base):
        raise ValueError("--base-only cannot be combined with node selection or --skip-base")

    selected_nodes = [] if args.base_only else select_nodes(inventory, args.node, args.all)

    if not args.skip_base:
        build_base(inventory)
    else:
        run(["docker", "image", "inspect", inventory["release"]["base_image"]], stdout=subprocess.DEVNULL)

    if args.base_only:
        return
    if args.all:
        with ThreadPoolExecutor(max_workers=len(selected_nodes)) as executor:
            futures = [
                executor.submit(build_node, inventory, node, args.output_dir)
                for node in selected_nodes
            ]
            for future in futures:
                future.result()
    else:
        build_node(inventory, selected_nodes[0], args.output_dir)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
