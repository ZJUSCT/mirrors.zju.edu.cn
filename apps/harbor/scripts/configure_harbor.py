#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests",
#     "pyyaml",
# ]
# ///
"""
Harbor declarative configuration script (registries + system settings).

Reads config.yaml, prompts interactively for credentials, then applies
settings via the Harbor REST API (v2.0) with HTTP Basic auth.
Idempotent: existing registries are left untouched.

Usage:
    python configure_harbor.py              # dry-run (print planned changes)
    python configure_harbor.py --apply      # apply changes to Harbor
    python configure_harbor.py --apply -v   # verbose output
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

BASE_PATH = Path(__file__).resolve().parent
DEFAULT_URL = "https://harbor.mirrors.zjusct.io"
DEFAULT_USER = "admin"
API_BASE = "/api/v2.0"

logger = logging.getLogger("harbor-config")


class HarborClient:
    def __init__(self, url: str, username: str, password: str):
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.base = url.rstrip("/")
        self._dry_run = False
        self._registry_cache: dict[str, int] = {}
        self._fetch_csrf_token()

    def _fetch_csrf_token(self):
        """Obtain CSRF token required for POST/PUT requests.

        GET /c/ctx sets a session cookie; once it exists Harbor's CSRF
        middleware rejects mutating requests without X-Harbor-CSRF-Token.
        """
        r = self.session.get(f"{self.base}/c/ctx")
        token = r.headers.get("X-Harbor-CSRF-Token", "")
        if not token:
            logger.warning("Could not obtain CSRF token from /c/ctx")
        else:
            self.session.headers["X-Harbor-CSRF-Token"] = token

    # -- generic request helpers --

    def _url(self, path: str) -> str:
        return f"{self.base}{API_BASE}{path}"

    def get(self, path: str, **kwargs) -> requests.Response:
        r = self.session.get(self._url(path), **kwargs)
        if r.status_code not in (200, 404):
            r.raise_for_status()
        return r

    def post(self, path: str, **kwargs) -> requests.Response:
        if self._dry_run:
            return requests.Response()
        return self.session.post(self._url(path), **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        if self._dry_run:
            return requests.Response()
        return self.session.put(self._url(path), **kwargs)

    # -- registry helpers --

    def list_registries(self) -> list[dict]:
        r = self.get("/registries", params={"page_size": 100})
        if r.status_code == 200:
            return r.json()
        return []

    def registry_id_by_name(self, name: str) -> int | None:
        if name in self._registry_cache:
            return self._registry_cache[name]
        for reg in self.list_registries():
            self._registry_cache[reg["name"]] = reg["id"]
        return self._registry_cache.get(name)

    def create_registry(self, reg: dict) -> None:
        existing = {r["name"]: r for r in self.list_registries()}
        if reg["name"] in existing:
            logger.info("  Registry '%s' already exists (id=%d), skipping",
                        reg["name"], existing[reg["name"]]["id"])
            return

        payload = {
            "name": reg["name"],
            "type": reg["type"],
            "insecure": reg.get("insecure", False),
        }
        # docker-hub / github-ghcr embed their URL; only other types take one.
        if reg.get("url"):
            payload["url"] = reg["url"]
        if reg.get("description"):
            payload["description"] = reg["description"]
        if reg.get("credential"):
            payload["credential"] = reg["credential"]

        if self._dry_run:
            logger.info("  Would create registry '%s' (%s)", reg["name"], reg["type"])
            return
        r = self.post("/registries", json=payload)
        if r.status_code == 201:
            loc = r.headers.get("Location", "")
            new_id = int(loc.split("/")[-1]) if loc else None
            if new_id is not None:
                self._registry_cache[reg["name"]] = new_id
            logger.info("  Created registry '%s' (id=%s)", reg["name"], new_id)
        elif r.status_code == 409:
            logger.info("  Registry '%s' already exists", reg["name"])
        else:
            logger.error("  Failed to create registry '%s': %d %s",
                         reg["name"], r.status_code, r.text)

    # -- project helpers --

    def list_projects(self) -> list[dict]:
        r = self.get("/projects", params={"page_size": 100})
        if r.status_code == 200:
            return r.json()
        return []

    def project_by_name(self, name: str) -> dict | None:
        for p in self.list_projects():
            if p["name"] == name:
                return p
        return None

    def _project_metadata(self, proj: dict) -> dict[str, str]:
        metadata = {
            "public": str(proj.get("public", False)).lower(),
        }
        if proj.get("metadata"):
            metadata.update({k: str(v).lower() for k, v in proj["metadata"].items()})
        return metadata

    def sync_project_metadata(self, proj: dict) -> None:
        """Ensure declared project metadata is present on existing projects."""
        desired = self._project_metadata(proj)
        if not desired:
            return

        project_name = quote(proj["name"], safe="")
        headers = {"X-Is-Resource-Name": "true"}
        r = self.get(f"/projects/{project_name}/metadatas/", headers=headers)
        if r.status_code != 200:
            logger.warning("  Failed to get metadata for project '%s': %d %s",
                           proj["name"], r.status_code, r.text)
            return
        current = r.json()

        for key, value in desired.items():
            if current.get(key) == value:
                continue
            payload = {key: value}
            if self._dry_run:
                logger.info("  Project '%s' metadata %s: %s -> %s",
                            proj["name"], key, current.get(key), value)
                continue
            if key in current:
                r = self.put(f"/projects/{project_name}/metadatas/{key}",
                             json=payload, headers=headers)
            else:
                r = self.post(f"/projects/{project_name}/metadatas/",
                              json=payload, headers=headers)
            if r.status_code == 200:
                logger.info("  Updated project '%s' metadata %s=%s",
                            proj["name"], key, value)
            else:
                logger.error("  Failed to update project '%s' metadata %s: %d %s",
                             proj["name"], key, r.status_code, r.text)

    def create_project(self, proj: dict) -> None:
        existing = self.project_by_name(proj["name"])
        if existing:
            logger.info("  Project '%s' already exists (id=%d)",
                        proj["name"], existing["project_id"])
            self.sync_project_metadata(proj)
            return

        payload: dict = {
            "project_name": proj["name"],
            "metadata": self._project_metadata(proj),
        }

        if proj.get("registry"):
            reg_id = self.registry_id_by_name(proj["registry"])
            if reg_id is None:
                logger.warning("  Registry '%s' not found, skipping proxy cache project '%s'",
                               proj["registry"], proj["name"])
                return
            payload["registry_id"] = reg_id

        if proj.get("storage_limit") is not None:
            payload["storage_limit"] = proj["storage_limit"]

        if self._dry_run:
            logger.info("  Would create project '%s'", proj["name"])
            return

        r = self.post("/projects", json=payload)
        if r.status_code == 201:
            logger.info("  Created project '%s'", proj["name"])
            self.sync_project_metadata(proj)
        else:
            logger.error("  Failed to create project '%s': %d %s",
                         proj["name"], r.status_code, r.text)

    # -- system configuration --

    def update_system_config(self, config: dict) -> None:
        if not config:
            return
        logger.info("Applying system configuration (%d keys)", len(config))
        if self._dry_run:
            for k, v in config.items():
                logger.info("  %s = %s", k, v)
            return
        r = self.put("/configurations", json=config)
        if r.status_code == 200:
            logger.info("  System configuration updated")
        else:
            logger.warning("  Failed to update system config: %d %s",
                           r.status_code, r.text)


def load_config() -> dict:
    with open(BASE_PATH / "config.yaml") as f:
        return yaml.safe_load(f) or {}


def prompt_credentials() -> tuple[str, str, str]:
    url = input(f"Harbor URL [{DEFAULT_URL}]: ").strip() or DEFAULT_URL
    user = input(f"Username [{DEFAULT_USER}]: ").strip() or DEFAULT_USER
    password = getpass.getpass(f"Password for {user}: ")
    if not password:
        logger.error("Empty password")
        sys.exit(1)
    return url, user, password


def main():
    parser = argparse.ArgumentParser(description="Declarative Harbor configuration")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    url, user, password = prompt_credentials()
    config = load_config()
    client = HarborClient(url, user, password)
    client._dry_run = not args.apply
    if not args.apply:
        # dry-run: declared-but-not-yet-created registries get placeholder ids
        # so dependent projects show up in the plan (apply resolves real ids)
        for i, reg in enumerate(config.get("registries", [])):
            client._registry_cache.setdefault(reg["name"], 1000 + i)

    mode = "APPLY" if args.apply else "DRY-RUN"
    logger.info("=== Harbor configuration [%s] ===", mode)

    system = config.get("system", {})
    if system:
        logger.info("System settings")
        client.update_system_config(system)

    registries = config.get("registries", [])
    if registries:
        logger.info("Registry endpoints (%d)", len(registries))
        for reg in registries:
            client.create_registry(reg)

    projects = config.get("projects", [])
    if projects:
        logger.info("Projects (%d)", len(projects))
        for proj in projects:
            client.create_project(proj)

    logger.info("=== Done [%s] ===", mode)


if __name__ == "__main__":
    main()
