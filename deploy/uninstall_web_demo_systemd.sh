#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-lab-safe-assistant-web-demo}"
SERVICE_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SERVICE_DIR}/${SERVICE_NAME}.service"

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
  systemctl --user daemon-reload || true
fi

if [[ -f "${SERVICE_FILE}" ]]; then
  rm -f "${SERVICE_FILE}"
  echo "[ok] removed service file: ${SERVICE_FILE}"
else
  echo "[info] service file not found: ${SERVICE_FILE}"
fi

echo "[ok] uninstall done."
