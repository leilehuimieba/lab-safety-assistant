#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

EMBED_CONTAINER="${EMBED_CONTAINER:-fake-ollama}"
EMBED_IMAGE="${EMBED_IMAGE:-python:3.11-slim}"
EMBED_NETWORK="${EMBED_NETWORK:-docker_default}"
EMBED_HOST_ALIAS="${EMBED_HOST_ALIAS:-host.docker.internal}"
EMBED_PORT="${EMBED_PORT:-11434}"

TARGET_CONTAINERS=("${@:-docker-api-1 docker-worker-1 docker-plugin_daemon-1}")
if [[ ${#TARGET_CONTAINERS[@]} -eq 1 && "${TARGET_CONTAINERS[0]}" == *" "* ]]; then
  # split when default came in as one spaced token
  read -r -a TARGET_CONTAINERS <<<"${TARGET_CONTAINERS[0]}"
fi

strip_cr() {
  printf '%s' "${1//$'\r'/}"
}

EMBED_CONTAINER="$(strip_cr "$EMBED_CONTAINER")"
EMBED_IMAGE="$(strip_cr "$EMBED_IMAGE")"
EMBED_NETWORK="$(strip_cr "$EMBED_NETWORK")"
EMBED_HOST_ALIAS="$(strip_cr "$EMBED_HOST_ALIAS")"
EMBED_PORT="$(strip_cr "$EMBED_PORT")"

echo "[embedding] root: $ROOT_DIR"
echo "[embedding] container: $EMBED_CONTAINER"
echo "[embedding] image: $EMBED_IMAGE"
echo "[embedding] network: $EMBED_NETWORK"
echo "[embedding] host alias: $EMBED_HOST_ALIAS"
echo "[embedding] port: $EMBED_PORT"
echo "[embedding] target containers: ${TARGET_CONTAINERS[*]}"

if ! docker network inspect "$EMBED_NETWORK" >/dev/null 2>&1; then
  echo "[embedding] network not found: $EMBED_NETWORK" >&2
  exit 2
fi

if docker ps --format '{{.Names}}' | grep -qx "$EMBED_CONTAINER"; then
  echo "[embedding] container already running: $EMBED_CONTAINER"
else
  if docker ps -a --format '{{.Names}}' | grep -qx "$EMBED_CONTAINER"; then
    echo "[embedding] removing stale container: $EMBED_CONTAINER"
    docker rm -f "$EMBED_CONTAINER" >/dev/null
  fi
  echo "[embedding] starting fake embedding container..."
  docker run -d \
    --name "$EMBED_CONTAINER" \
    --network "$EMBED_NETWORK" \
    -p "${EMBED_PORT}:11434" \
    -v "$ROOT_DIR/deploy/fake_ollama_embed.py:/app/fake_ollama_embed.py:ro" \
    "$EMBED_IMAGE" \
    python /app/fake_ollama_embed.py >/dev/null
fi

python3 scripts/fix_embedding_host_mapping.py \
  --embed-container "$EMBED_CONTAINER" \
  --target-host "$EMBED_HOST_ALIAS" \
  --target-port "$EMBED_PORT" \
  --containers "${TARGET_CONTAINERS[@]}"

for c in "${TARGET_CONTAINERS[@]}"; do
  echo "[embedding] verify $c -> $EMBED_HOST_ALIAS:$EMBED_PORT"
  docker exec "$c" sh -lc "curl -sS -m 3 http://$EMBED_HOST_ALIAS:$EMBED_PORT/api/tags >/dev/null"
done

echo "[embedding] channel ready."
