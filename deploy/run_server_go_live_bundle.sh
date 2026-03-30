#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${1:-$ROOT_DIR/deploy/env/go_live_bundle.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] env file not found: $ENV_FILE" >&2
  echo "Use template: deploy/env/go_live_bundle.example.env" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

strip_cr_var() {
  local name="$1"
  local value="${!name-}"
  value="${value//$'\r'/}"
  printf -v "$name" "%s" "$value"
}

for var in \
  DIFY_TENANT_ID DIFY_APP_TOKEN DIFY_ENDPOINT_URL OPENAI_COMPAT_API_KEY \
  DIFY_WORKFLOW_ID DIFY_API_BASE DIFY_PROVIDER_NAME DIFY_MODEL_NAME \
  DIFY_ENDPOINT_MODEL_NAME DIFY_MODEL_TYPE DIFY_FALLBACK_MODEL \
  DIFY_FORCE_ROTATE_KEY \
  AUTO_FIX_EMBEDDING_CHANNEL EMBEDDING_TARGET_CONTAINERS \
  DIFY_SMOKE_QUERY DIFY_SMOKE_USER DIFY_SMOKE_TIMEOUT_SEC \
  RELEASE_DIR WEB_HEALTH_URL STABILITY_ROUNDS STABILITY_INTERVAL_SEC \
  STABILITY_LIMIT STABILITY_DIFY_TIMEOUT STABILITY_EVAL_CONCURRENCY \
  STABILITY_RETRY_ON_TIMEOUT STABILITY_FAILOVER_DAYS STABILITY_FAIL_STREAK_THRESHOLD \
  STABILITY_SKIP_HEALTH_CHECK STABILITY_SKIP_CANARY RELEASE_POLICY_PROFILE \
  RELEASE_POLICY_RUN_SECONDARY RELEASE_POLICY_SECONDARY_PROFILE \
  RELEASE_POLICY_ENFORCE_SECONDARY RELEASE_POLICY_STRICT DIFY_API_CONTAINER; do
  strip_cr_var "$var"
done

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "[ERROR] required env is empty: $name" >&2
    exit 3
  fi
}

require_var "DIFY_TENANT_ID"
require_var "DIFY_APP_TOKEN"
require_var "DIFY_ENDPOINT_URL"
require_var "OPENAI_COMPAT_API_KEY"
require_var "DIFY_WORKFLOW_ID"

# Release policy relies on statistically meaningful sample size.
if [[ -z "${STABILITY_LIMIT:-}" ]]; then
  STABILITY_LIMIT=20
fi
if [[ "${STABILITY_LIMIT}" =~ ^[0-9]+$ ]] && (( STABILITY_LIMIT < 20 )); then
  echo "[bundle] STABILITY_LIMIT=${STABILITY_LIMIT} is too small for release policy; auto-upgrade to 20."
  STABILITY_LIMIT=20
fi

RUN_TAG="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$ROOT_DIR/artifacts/go_live_bundle/run_${RUN_TAG}"
mkdir -p "$OUT_DIR"

RECOVERY_LOG="$OUT_DIR/01_provider_recovery.log"
EMBEDDING_LOG="$OUT_DIR/02_embedding_channel.log"
STABILITY_LOG="$OUT_DIR/03_release_stability.log"
PREFLIGHT_LOG="$OUT_DIR/04_go_live_preflight.log"
DIGEST_LOG="$OUT_DIR/05_failure_digest.log"
SNAPSHOT_LOG="$OUT_DIR/06_runtime_snapshot.log"

RECOVERY_EXIT=0
EMBEDDING_EXIT=0
PREFLIGHT_EXIT=0
STABILITY_EXIT=0
DIGEST_EXIT=0
SNAPSHOT_EXIT=0

run_with_log() {
  local log_file="$1"
  shift
  set +e
  "$@" | tee "$log_file"
  local rc=${PIPESTATUS[0]}
  set -e
  return $rc
}

echo "[bundle] run tag: $RUN_TAG"
echo "[bundle] output dir: $OUT_DIR"
echo "[bundle] env file: $ENV_FILE"

echo "[bundle] step1/4 provider recovery + workflow smoke"
if run_with_log "$RECOVERY_LOG" "$ROOT_DIR/scripts/run_dify_provider_recovery_and_smoke.sh" "$ENV_FILE"; then
  RECOVERY_EXIT=0
else
  RECOVERY_EXIT=$?
fi

echo "[bundle] step2/4 embedding channel ensure"
if [[ "${AUTO_FIX_EMBEDDING_CHANNEL:-1}" == "1" ]]; then
  EMBEDDING_CONTAINER_ARGS=()
  if [[ -n "${EMBEDDING_TARGET_CONTAINERS:-}" ]]; then
    # shellcheck disable=SC2206
    EMBEDDING_CONTAINER_ARGS=(${EMBEDDING_TARGET_CONTAINERS})
  fi
  if run_with_log "$EMBEDDING_LOG" "$ROOT_DIR/deploy/ensure_embedding_channel.sh" "${EMBEDDING_CONTAINER_ARGS[@]}"; then
    EMBEDDING_EXIT=0
  else
    EMBEDDING_EXIT=$?
  fi
else
  echo "[bundle] AUTO_FIX_EMBEDDING_CHANNEL=0, skip embedding ensure." | tee "$EMBEDDING_LOG"
  EMBEDDING_EXIT=0
fi

echo "[bundle] step3/4 release stability check"
STABILITY_ARGS=(
  --repo-root .
  --rounds "${STABILITY_ROUNDS:-3}"
  --interval-sec "${STABILITY_INTERVAL_SEC:-30}"
  --continue-on-fail
  --workflow-id "${DIFY_WORKFLOW_ID}"
  --primary-model "${DIFY_MODEL_NAME:-gpt-5.2-codex}"
  --fallback-model "${DIFY_FALLBACK_MODEL:-${DIFY_MODEL_NAME:-gpt-5.2-codex}}"
  --dify-base-url "${DIFY_API_BASE:-http://127.0.0.1:8080}"
  --dify-app-key "${DIFY_APP_TOKEN}"
  --limit "${STABILITY_LIMIT:-20}"
  --dify-timeout "${STABILITY_DIFY_TIMEOUT:-180}"
  --eval-concurrency "${STABILITY_EVAL_CONCURRENCY:-1}"
  --retry-on-timeout "${STABILITY_RETRY_ON_TIMEOUT:-1}"
  --failover-days "${STABILITY_FAILOVER_DAYS:-1}"
  --failover-fail-streak-threshold "${STABILITY_FAIL_STREAK_THRESHOLD:-2}"
  --release-policy-profile "${RELEASE_POLICY_PROFILE:-demo}"
)

if [[ "${STABILITY_SKIP_HEALTH_CHECK:-0}" == "1" ]]; then
  STABILITY_ARGS+=(--skip-health-check)
fi
if [[ "${STABILITY_SKIP_CANARY:-0}" == "1" ]]; then
  STABILITY_ARGS+=(--skip-canary)
fi
if [[ "${RELEASE_POLICY_RUN_SECONDARY:-0}" == "1" ]]; then
  STABILITY_ARGS+=(--release-policy-run-secondary --release-policy-secondary-profile "${RELEASE_POLICY_SECONDARY_PROFILE:-prod}")
fi
if [[ "${RELEASE_POLICY_ENFORCE_SECONDARY:-0}" == "1" ]]; then
  STABILITY_ARGS+=(--release-policy-enforce-secondary)
fi
if [[ "${RELEASE_POLICY_STRICT:-0}" == "1" ]]; then
  STABILITY_ARGS+=(--release-policy-strict)
fi

if run_with_log "$STABILITY_LOG" python3 scripts/release/run_release_stability_check.py "${STABILITY_ARGS[@]}"; then
  STABILITY_EXIT=0
else
  STABILITY_EXIT=$?
fi

echo "[bundle] step4/4 go-live preflight"
if run_with_log "$PREFLIGHT_LOG" python3 scripts/release/go_live_preflight.py \
  --repo-root . \
  --release-dir "${RELEASE_DIR:-release_exports/v8.1}" \
  --web-health-url "${WEB_HEALTH_URL:-http://127.0.0.1:${DEMO_PORT:-8088}/health}" \
  --output-json "docs/ops/go_live_readiness.json" \
  --output-md "docs/ops/go_live_readiness.md"; then
  PREFLIGHT_EXIT=0
else
  PREFLIGHT_EXIT=$?
fi

echo "[bundle] diagnostics: failure digest"
if run_with_log "$DIGEST_LOG" python3 scripts/release/generate_go_live_failure_digest.py --repo-root .; then
  DIGEST_EXIT=0
else
  DIGEST_EXIT=$?
fi

echo "[bundle] diagnostics: runtime profile snapshot"
if run_with_log "$SNAPSHOT_LOG" python3 scripts/release/generate_runtime_profile_snapshot.py --repo-root . --env-file "$ENV_FILE"; then
  SNAPSHOT_EXIT=0
else
  SNAPSHOT_EXIT=$?
fi

echo "[bundle] finalize summary"
python3 - "$ROOT_DIR" "$OUT_DIR" "$RECOVERY_EXIT" "$EMBEDDING_EXIT" "$PREFLIGHT_EXIT" "$STABILITY_EXIT" "$DIGEST_EXIT" "$SNAPSHOT_EXIT" <<'PY'
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2]).resolve()
recovery_exit = int(sys.argv[3])
embedding_exit = int(sys.argv[4])
preflight_exit = int(sys.argv[5])
stability_exit = int(sys.argv[6])
digest_exit = int(sys.argv[7])
snapshot_exit = int(sys.argv[8])

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

go_live = load_json(root / "docs/ops/go_live_readiness.json")
stability = load_json(root / "docs/eval/release_stability_check.json")

go_live_overall = str(go_live.get("overall", "")).strip().upper()
stability_overall = str(stability.get("overall", "")).strip().upper()

overall = "PASS"
if recovery_exit != 0 or preflight_exit != 0 or stability_exit != 0:
    overall = "BLOCK"
if embedding_exit != 0:
    overall = "BLOCK"
if go_live_overall not in {"PASS"}:
    overall = "BLOCK"
if stability_overall not in {"PASS"}:
    overall = "BLOCK"

payload = {
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "overall": overall,
    "steps": {
        "provider_recovery_and_smoke": {"exit_code": recovery_exit, "ok": recovery_exit == 0},
        "embedding_channel_ensure": {"exit_code": embedding_exit, "ok": embedding_exit == 0},
        "go_live_preflight": {
            "exit_code": preflight_exit,
            "ok": preflight_exit == 0,
            "overall": go_live_overall or "UNKNOWN",
        },
        "release_stability_check": {
            "exit_code": stability_exit,
            "ok": stability_exit == 0,
            "overall": stability_overall or "UNKNOWN",
        },
        "failure_digest": {"exit_code": digest_exit, "ok": digest_exit == 0},
        "runtime_profile_snapshot": {"exit_code": snapshot_exit, "ok": snapshot_exit == 0},
    },
    "artifacts": {
        "bundle_output_dir": str(out_dir),
        "go_live_readiness_json": str(root / "docs/ops/go_live_readiness.json"),
        "go_live_readiness_md": str(root / "docs/ops/go_live_readiness.md"),
        "release_stability_json": str(root / "docs/eval/release_stability_check.json"),
        "release_stability_md": str(root / "docs/eval/release_stability_check.md"),
        "failure_digest_json": str(root / "docs/ops/go_live_failure_digest_latest.json"),
        "failure_digest_md": str(root / "docs/ops/go_live_failure_digest_latest.md"),
        "runtime_profile_snapshot_json": str(root / "docs/ops/runtime_profile_snapshot.json"),
        "runtime_profile_snapshot_md": str(root / "docs/ops/runtime_profile_snapshot.md"),
    },
}

json_path = root / "docs/ops/go_live_bundle_latest.json"
md_path = root / "docs/ops/go_live_bundle_latest.md"
json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

lines = []
lines.append("# Go Live Bundle Result")
lines.append("")
lines.append(f"- Generated: `{payload['generated_at']}`")
lines.append(f"- Overall: `{payload['overall']}`")
lines.append("")
lines.append("## Step Status")
for name, info in payload["steps"].items():
    line = f"- {name}: exit={info.get('exit_code')} ok={info.get('ok')}"
    if "overall" in info:
        line += f" overall={info.get('overall')}"
    lines.append(line)
lines.append("")
lines.append("## Artifacts")
for k, v in payload["artifacts"].items():
    lines.append(f"- {k}: `{v}`")
lines.append("")
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

# Re-sync digest with the latest bundle summary just written above.
python3 scripts/release/generate_go_live_failure_digest.py --repo-root . >/dev/null 2>&1 || true

FINAL_OVERALL="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path("docs/ops/go_live_bundle_latest.json")
if p.exists():
    data=json.loads(p.read_text(encoding="utf-8"))
    print(data.get("overall","BLOCK"))
else:
    print("BLOCK")
PY
)"

if [[ "$FINAL_OVERALL" == "PASS" ]]; then
  echo "[bundle] PASS"
  exit 0
fi

echo "[bundle] BLOCK"
exit 4
