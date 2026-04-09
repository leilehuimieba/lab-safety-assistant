#!/usr/bin/env python3
"""
One-click recovery + smoke test for Dify openai_api_compatible provider.

What this script does:
1) Regenerate tenant RSA keypair in Dify and persist private key in storage.
2) Re-encrypt API key with the new tenant public key.
3) Upsert provider-level/model-level credentials for openai_api_compatible.
4) Run one real workflow call via /v1/chat-messages and assert success.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests


DEFAULT_PROVIDER = "langgenius/openai_api_compatible/openai_api_compatible"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_MODEL_TYPE = "llm"
DEFAULT_API_BASE = "http://127.0.0.1:8080"
DEFAULT_QUERY = "实验室发生化学品泄漏时，第一步怎么做？"


@dataclass
class SmokeResult:
    http_status: int
    workflow_status: Optional[str]
    workflow_run_id: Optional[str]
    answer: str
    error_message: Optional[str]


def _run(cmd: list[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def detect_api_container(preferred: Optional[str]) -> str:
    if preferred:
        return preferred

    p = _run(["docker", "ps", "--format", "{{.Names}}"])
    if p.returncode != 0:
        raise RuntimeError(f"docker ps failed: {p.stderr.strip()}")

    names = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    for name in names:
        if name.endswith("-api-1"):
            return name
    for name in names:
        if "api-1" in name:
            return name
    for name in names:
        if "api" in name:
            return name
    raise RuntimeError("Cannot detect Dify API container name. Please pass --api-container.")


def run_fix_in_api_container(
    api_container: str,
    tenant_id: str,
    provider_name: str,
    model_name: str,
    model_type: str,
    endpoint_url: str,
    endpoint_model_name: str,
    api_key: str,
    force_rotate_key: bool,
) -> dict:
    container_script = r"""
import base64
import json
import os

from app import create_app
from extensions.ext_database import db
from extensions.ext_redis import redis_client
from extensions.ext_storage import storage
from core.helper.model_provider_cache import ProviderCredentialsCache, ProviderCredentialsCacheType
from libs.rsa import encrypt, generate_key_pair
from models.account import Tenant
from models.provider import Provider, ProviderCredential, ProviderModel, ProviderModelCredential, ProviderModelSetting

TENANT_ID = os.environ["TENANT_ID"]
PROVIDER_NAME = os.environ["PROVIDER_NAME"]
MODEL_NAME = os.environ["MODEL_NAME"]
MODEL_TYPE = os.environ["MODEL_TYPE"]
ENDPOINT_URL = os.environ["ENDPOINT_URL"]
ENDPOINT_MODEL_NAME = os.environ["ENDPOINT_MODEL_NAME"]
API_KEY = os.environ["API_KEY"]
FORCE_ROTATE_KEY = os.environ.get("FORCE_ROTATE_KEY", "0").strip() in {"1", "true", "TRUE", "yes", "YES"}

app = create_app()

with app.app_context():
    tenant = db.session.query(Tenant).filter(Tenant.id == TENANT_ID).first()
    if not tenant:
        raise RuntimeError(f"tenant not found: {TENANT_ID}")

    priv_path = f"privkeys/{TENANT_ID}/private.pem"
    private_exists = True
    try:
        storage.load(priv_path)
    except FileNotFoundError:
        private_exists = False

    key_rotated = False
    if FORCE_ROTATE_KEY or (not private_exists) or (not tenant.encrypt_public_key):
        # Recreate key pair only when forced or key material is missing.
        new_public_key = generate_key_pair(TENANT_ID)
        tenant.encrypt_public_key = new_public_key
        key_rotated = True
    else:
        new_public_key = tenant.encrypt_public_key

    encrypted_api_key = base64.b64encode(encrypt(API_KEY, new_public_key)).decode()

    base_cfg = {
        "api_key": encrypted_api_key,
        "endpoint_url": ENDPOINT_URL,
        "mode": "chat",
        "context_size": "4096",
        "max_tokens_to_sample": "4096",
        "agent_thought_support": "not_supported",
        "compatibility_mode": "strict",
        "function_calling_type": "no_call",
        "stream_function_calling": "not_supported",
        "vision_support": "no_support",
        "structured_output_support": "not_supported",
        "stream_mode_auth": "not_use",
        "stream_mode_delimiter": "\\n\\n",
    }

    provider_credential = (
        db.session.query(ProviderCredential)
        .filter(
            ProviderCredential.tenant_id == TENANT_ID,
            ProviderCredential.provider_name == PROVIDER_NAME,
        )
        .order_by(ProviderCredential.updated_at.desc())
        .first()
    )
    created_provider_credential = False
    if not provider_credential:
        provider_credential = ProviderCredential(
            tenant_id=TENANT_ID,
            provider_name=PROVIDER_NAME,
            credential_name="default",
            encrypted_config="{}",
        )
        db.session.add(provider_credential)
        created_provider_credential = True

    provider_credential.encrypted_config = json.dumps(base_cfg, ensure_ascii=False)
    provider_credential.credential_name = provider_credential.credential_name or "default"

    model_credential = (
        db.session.query(ProviderModelCredential)
        .filter(
            ProviderModelCredential.tenant_id == TENANT_ID,
            ProviderModelCredential.provider_name == PROVIDER_NAME,
            ProviderModelCredential.model_name == MODEL_NAME,
            ProviderModelCredential.model_type == MODEL_TYPE,
        )
        .order_by(ProviderModelCredential.updated_at.desc())
        .first()
    )
    created_model_credential = False
    if not model_credential:
        model_credential = ProviderModelCredential(
            tenant_id=TENANT_ID,
            provider_name=PROVIDER_NAME,
            model_name=MODEL_NAME,
            model_type=MODEL_TYPE,
            credential_name=provider_credential.credential_name or "default",
            encrypted_config="{}",
        )
        db.session.add(model_credential)
        created_model_credential = True

    try:
        model_cfg = json.loads(model_credential.encrypted_config or "{}")
    except Exception:
        model_cfg = {}
    model_cfg.update(base_cfg)
    model_cfg.update(
        {
            "display_name": MODEL_NAME,
            "endpoint_model_name": ENDPOINT_MODEL_NAME,
        }
    )
    model_credential.encrypted_config = json.dumps(model_cfg, ensure_ascii=False)
    model_credential.model_type = MODEL_TYPE
    model_credential.credential_name = provider_credential.credential_name or "default"

    provider_row = (
        db.session.query(Provider)
        .filter(
            Provider.tenant_id == TENANT_ID,
            Provider.provider_name == PROVIDER_NAME,
        )
        .order_by(Provider.updated_at.desc())
        .first()
    )
    created_provider_row = False
    if not provider_row:
        provider_row = Provider(
            tenant_id=TENANT_ID,
            provider_name=PROVIDER_NAME,
            provider_type="custom",
            is_valid=True,
            quota_type="",
            credential_id=provider_credential.id,
        )
        db.session.add(provider_row)
        created_provider_row = True
    else:
        provider_row.is_valid = True
        provider_row.credential_id = provider_credential.id

    legacy_model_credential_ids = []

    # Remove legacy rows that map the same model name through deprecated model types.
    if MODEL_TYPE == "llm":
        legacy_model_credentials = (
            db.session.query(ProviderModelCredential)
            .filter(
                ProviderModelCredential.tenant_id == TENANT_ID,
                ProviderModelCredential.provider_name == PROVIDER_NAME,
                ProviderModelCredential.model_name == MODEL_NAME,
                ProviderModelCredential.model_type != MODEL_TYPE,
            )
            .all()
        )
        legacy_model_credential_ids = [item.id for item in legacy_model_credentials]
        for legacy_credential in legacy_model_credentials:
            db.session.delete(legacy_credential)

        legacy_provider_model_rows = (
            db.session.query(ProviderModel)
            .filter(
                ProviderModel.tenant_id == TENANT_ID,
                ProviderModel.provider_name == PROVIDER_NAME,
                ProviderModel.model_name == MODEL_NAME,
                ProviderModel.model_type != MODEL_TYPE,
            )
            .all()
        )
        for legacy_row in legacy_provider_model_rows:
            db.session.delete(legacy_row)

    provider_model_row = (
        db.session.query(ProviderModel)
        .filter(
            ProviderModel.tenant_id == TENANT_ID,
            ProviderModel.provider_name == PROVIDER_NAME,
            ProviderModel.model_name == MODEL_NAME,
            ProviderModel.model_type == MODEL_TYPE,
        )
        .order_by(ProviderModel.updated_at.desc())
        .first()
    )
    created_provider_model_row = False
    if not provider_model_row:
        provider_model_row = ProviderModel(
            tenant_id=TENANT_ID,
            provider_name=PROVIDER_NAME,
            model_name=MODEL_NAME,
            model_type=MODEL_TYPE,
            is_valid=True,
            credential_id=model_credential.id,
        )
        db.session.add(provider_model_row)
        created_provider_model_row = True
    else:
        provider_model_row.is_valid = True
        provider_model_row.credential_id = model_credential.id

    provider_model_setting = (
        db.session.query(ProviderModelSetting)
        .filter(
            ProviderModelSetting.tenant_id == TENANT_ID,
            ProviderModelSetting.provider_name == PROVIDER_NAME,
            ProviderModelSetting.model_name == MODEL_NAME,
            ProviderModelSetting.model_type == MODEL_TYPE,
        )
        .first()
    )
    created_provider_model_setting = False
    if not provider_model_setting:
        provider_model_setting = ProviderModelSetting(
            tenant_id=TENANT_ID,
            provider_name=PROVIDER_NAME,
            model_name=MODEL_NAME,
            model_type=MODEL_TYPE,
            enabled=True,
            load_balancing_enabled=False,
        )
        db.session.add(provider_model_setting)
        created_provider_model_setting = True
    else:
        provider_model_setting.enabled = True

    db.session.commit()

    ProviderCredentialsCache(
        tenant_id=TENANT_ID,
        identity_id=provider_row.id,
        cache_type=ProviderCredentialsCacheType.PROVIDER,
    ).delete()
    ProviderCredentialsCache(
        tenant_id=TENANT_ID,
        identity_id=provider_model_row.id,
        cache_type=ProviderCredentialsCacheType.MODEL,
    ).delete()
    redis_client.delete(f"provider_configurations:{TENANT_ID}")

    private_pem = storage.load(priv_path)

    print(
        json.dumps(
            {
                "tenant_id": TENANT_ID,
                "provider_name": PROVIDER_NAME,
                "model_name": MODEL_NAME,
                "provider_credential_created": created_provider_credential,
                "model_credential_created": created_model_credential,
                "provider_row_created": created_provider_row,
                "provider_model_row_created": created_provider_model_row,
                "provider_model_setting_created": created_provider_model_setting,
                "provider_credential_id": provider_credential.id,
                "model_credential_id": model_credential.id,
                "provider_row_credential_id": provider_row.credential_id,
                "provider_model_row_credential_id": provider_model_row.credential_id,
                "legacy_model_credential_ids_removed": legacy_model_credential_ids,
                "key_rotated": key_rotated,
                "private_key_bytes": len(private_pem),
            },
            ensure_ascii=False,
        )
    )
"""

    cmd = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"TENANT_ID={tenant_id}",
        "-e",
        f"PROVIDER_NAME={provider_name}",
        "-e",
        f"MODEL_NAME={model_name}",
        "-e",
        f"MODEL_TYPE={model_type}",
        "-e",
        f"ENDPOINT_URL={endpoint_url}",
        "-e",
        f"ENDPOINT_MODEL_NAME={endpoint_model_name}",
        "-e",
        f"API_KEY={api_key}",
        "-e",
        f"FORCE_ROTATE_KEY={'1' if force_rotate_key else '0'}",
        api_container,
        "python",
        "-",
    ]
    p = _run(cmd, input_text=container_script)
    if p.returncode != 0:
        raise RuntimeError(
            "Fix step failed in api container.\n"
            f"stdout:\n{p.stdout}\n"
            f"stderr:\n{p.stderr}"
        )

    raw = p.stdout.strip().splitlines()
    if not raw:
        raise RuntimeError("Fix step returned empty output.")

    try:
        return json.loads(raw[-1])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Fix step output is not valid JSON: {raw[-1]}") from e


def run_workflow_smoke(
    base_url: str,
    app_token: str,
    query: str,
    user: str,
    timeout_sec: int,
) -> SmokeResult:
    headers = {
        "Authorization": f"Bearer {app_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "streaming",
        "user": user,
    }

    response = requests.post(
        f"{base_url.rstrip('/')}/v1/chat-messages",
        headers=headers,
        json=payload,
        timeout=(20, timeout_sec),
        stream=True,
    )

    answer_parts: list[str] = []
    workflow_status = None
    workflow_run_id = None
    error_message = None

    if response.status_code != 200:
        return SmokeResult(
            http_status=response.status_code,
            workflow_status=None,
            workflow_run_id=None,
            answer="",
            error_message=f"http {response.status_code}: {response.text[:500]}",
        )

    for raw in response.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw.strip()
        if not line.startswith("data: "):
            continue

        data_str = line[6:]
        try:
            obj = json.loads(data_str)
        except Exception:
            continue

        event = obj.get("event")
        if event == "message":
            chunk = obj.get("answer") or ""
            if chunk:
                answer_parts.append(chunk)
        elif event == "workflow_finished":
            data = obj.get("data") or {}
            workflow_status = data.get("status")
            workflow_run_id = data.get("id")
            break
        elif event == "error":
            error_message = obj.get("message") or obj.get("error") or str(obj)
            break

    return SmokeResult(
        http_status=response.status_code,
        workflow_status=workflow_status,
        workflow_run_id=workflow_run_id,
        answer="".join(answer_parts).strip(),
        error_message=error_message,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recover Dify provider and run workflow smoke test.")
    parser.add_argument("--api-container", default=os.getenv("DIFY_API_CONTAINER"))
    parser.add_argument("--tenant-id", default=os.getenv("DIFY_TENANT_ID"), required=os.getenv("DIFY_TENANT_ID") is None)
    parser.add_argument("--provider-name", default=os.getenv("DIFY_PROVIDER_NAME", DEFAULT_PROVIDER))
    parser.add_argument("--model-name", default=os.getenv("DIFY_MODEL_NAME", DEFAULT_MODEL))
    parser.add_argument("--model-type", default=os.getenv("DIFY_MODEL_TYPE", DEFAULT_MODEL_TYPE))
    parser.add_argument("--endpoint-url", default=os.getenv("DIFY_ENDPOINT_URL"), required=os.getenv("DIFY_ENDPOINT_URL") is None)
    parser.add_argument("--endpoint-model-name", default=os.getenv("DIFY_ENDPOINT_MODEL_NAME", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_COMPAT_API_KEY"), required=os.getenv("OPENAI_COMPAT_API_KEY") is None)
    parser.add_argument("--app-token", default=os.getenv("DIFY_APP_TOKEN"), required=os.getenv("DIFY_APP_TOKEN") is None)
    parser.add_argument("--api-base", default=os.getenv("DIFY_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--query", default=os.getenv("DIFY_SMOKE_QUERY", DEFAULT_QUERY))
    parser.add_argument("--user", default=os.getenv("DIFY_SMOKE_USER", "recovery-smoke"))
    parser.add_argument("--timeout-sec", type=int, default=int(os.getenv("DIFY_SMOKE_TIMEOUT_SEC", "240")))
    parser.add_argument("--smoke-retries", type=int, default=int(os.getenv("DIFY_SMOKE_RETRIES", "3")))
    parser.add_argument(
        "--smoke-retry-interval-sec",
        type=float,
        default=float(os.getenv("DIFY_SMOKE_RETRY_INTERVAL_SEC", "3")),
    )
    parser.add_argument(
        "--force-rotate-key",
        action="store_true",
        default=str(os.getenv("DIFY_FORCE_ROTATE_KEY", "0")).strip() in {"1", "true", "TRUE", "yes", "YES"},
        help="Force rotate tenant RSA key pair before rewriting credentials.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        api_container = detect_api_container(args.api_container)
    except Exception as e:
        print(f"[ERROR] detect api container failed: {e}", file=sys.stderr)
        return 2

    print(f"[INFO] api_container={api_container}")
    print(f"[INFO] tenant_id={args.tenant_id}")
    print(f"[INFO] provider={args.provider_name}")
    print(f"[INFO] model={args.model_name}")
    print(f"[INFO] endpoint={args.endpoint_url}")

    try:
        fix_result = run_fix_in_api_container(
            api_container=api_container,
            tenant_id=args.tenant_id,
            provider_name=args.provider_name,
            model_name=args.model_name,
            model_type=args.model_type,
            endpoint_url=args.endpoint_url,
            endpoint_model_name=args.endpoint_model_name,
            api_key=args.api_key,
            force_rotate_key=bool(args.force_rotate_key),
        )
    except Exception as e:
        print(f"[ERROR] provider recovery failed: {e}", file=sys.stderr)
        return 3

    print("[INFO] provider recovery result:")
    print(json.dumps(fix_result, ensure_ascii=False, indent=2))

    retries = max(1, int(args.smoke_retries))
    smoke: Optional[SmokeResult] = None
    for idx in range(1, retries + 1):
        smoke = run_workflow_smoke(
            base_url=args.api_base,
            app_token=args.app_token,
            query=args.query,
            user=args.user,
            timeout_sec=args.timeout_sec,
        )
        ok_status = (smoke.workflow_status or "").lower() in {"success", "succeeded"}
        has_answer = bool(smoke.answer.strip())
        print(
            f"[INFO] smoke attempt {idx}/{retries}: "
            f"http={smoke.http_status}, status={smoke.workflow_status}, has_answer={has_answer}"
        )
        if smoke.http_status == 200 and ok_status and has_answer:
            break
        if idx < retries:
            time.sleep(max(0.5, float(args.smoke_retry_interval_sec)))

    assert smoke is not None

    print("[INFO] workflow smoke result:")
    print(
        json.dumps(
            {
                "http_status": smoke.http_status,
                "workflow_finished.status": smoke.workflow_status,
                "workflow_run_id": smoke.workflow_run_id,
                "answer_preview": smoke.answer[:300],
                "error_message": smoke.error_message,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    ok_status = (smoke.workflow_status or "").lower() in {"success", "succeeded"}
    has_answer = bool(smoke.answer.strip())
    if smoke.http_status == 200 and ok_status and has_answer:
        print("[PASS] workflow smoke passed with readable answer.")
        return 0

    print("[FAIL] workflow smoke did not pass acceptance.", file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
