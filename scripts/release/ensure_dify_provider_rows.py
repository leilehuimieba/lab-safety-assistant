#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys


DEFAULT_PROVIDERS = [
    "langgenius/openai_api_compatible/openai_api_compatible",
    "langgenius/ollama/ollama",
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def detect_api_container(preferred: str) -> str:
    if preferred.strip():
        return preferred.strip()
    completed = run(["docker", "ps", "--format", "{{.Names}}"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "docker ps failed")
    names = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    for name in names:
        if name.endswith("-api-1"):
            return name
    for name in names:
        if "api-1" in name:
            return name
    raise RuntimeError("cannot detect Dify API container")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure Dify provider rows exist for current tenant.")
    parser.add_argument("--api-container", default="", help="Dify API container name.")
    parser.add_argument("--tenant-id", default="", help="Tenant id. Auto-detect when omitted.")
    parser.add_argument(
        "--provider-name",
        action="append",
        default=[],
        help="Provider name to ensure. Repeatable. Default: openai_api_compatible + ollama.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    provider_names = [item.strip() for item in args.provider_name if item.strip()] or list(DEFAULT_PROVIDERS)
    api_container = detect_api_container(args.api_container)

    container_script = r"""
import json
import os

from app import create_app
from extensions.ext_database import db
from models.account import Tenant
from models.model import App
from models.provider import Provider, ProviderCredential

tenant_id = (os.environ.get("TENANT_ID") or "").strip()
provider_names = [item.strip() for item in (os.environ.get("PROVIDER_NAMES") or "").split("\n") if item.strip()]

app = create_app()
with app.app_context():
    if not tenant_id:
        tenants = db.session.query(Tenant).order_by(Tenant.created_at.asc()).all()
        if len(tenants) == 1:
            tenant_id = tenants[0].id
        else:
            latest_app = db.session.query(App).order_by(App.created_at.desc()).first()
            if latest_app:
                tenant_id = latest_app.tenant_id
    if not tenant_id:
        raise RuntimeError("cannot resolve tenant_id")

    results = []
    for provider_name in provider_names:
        credential = (
            db.session.query(ProviderCredential)
            .filter(
                ProviderCredential.tenant_id == tenant_id,
                ProviderCredential.provider_name == provider_name,
            )
            .order_by(ProviderCredential.updated_at.desc(), ProviderCredential.created_at.desc())
            .first()
        )
        if not credential:
            results.append({"provider_name": provider_name, "ok": False, "reason": "credential_missing"})
            continue

        row = (
            db.session.query(Provider)
            .filter(Provider.tenant_id == tenant_id, Provider.provider_name == provider_name)
            .order_by(Provider.updated_at.desc(), Provider.created_at.desc())
            .first()
        )
        created = False
        if not row:
            row = Provider(
                tenant_id=tenant_id,
                provider_name=provider_name,
                provider_type="custom",
                is_valid=True,
                quota_type="",
                credential_id=credential.id,
            )
            db.session.add(row)
            created = True
        else:
            row.is_valid = True
            row.provider_type = row.provider_type or "custom"
            row.credential_id = credential.id

        results.append(
            {
                "provider_name": provider_name,
                "ok": True,
                "created": created,
                "credential_id": str(credential.id),
            }
        )

    db.session.commit()
    print(json.dumps({"tenant_id": tenant_id, "results": results}, ensure_ascii=False))
"""

    completed = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "-e",
            f"TENANT_ID={args.tenant_id.strip()}",
            "-e",
            "PROVIDER_NAMES=" + "\n".join(provider_names),
            api_container,
            "python",
            "-c",
            container_script,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode

    print(completed.stdout.strip())
    try:
        payload = json.loads(completed.stdout.strip() or "{}")
    except Exception:
        print("[FAIL] cannot parse ensure result", file=sys.stderr)
        return 2

    failed = [item for item in payload.get("results", []) if not item.get("ok")]
    if failed:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
