#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REDACT_KEYWORDS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sanitized runtime profile snapshot.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--env-file",
        default="deploy/env/go_live_bundle.env",
        help="Primary env file for snapshot (sanitized).",
    )
    parser.add_argument(
        "--output-json",
        default="docs/ops/runtime_profile_snapshot.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/ops/runtime_profile_snapshot.md",
        help="Output markdown path.",
    )
    return parser.parse_args()


def resolve(repo_root: Path, rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    except Exception as e:  # noqa: BLE001
        return 1, str(e)
    out = (cp.stdout or "").strip()
    err = (cp.stderr or "").strip()
    return cp.returncode, out if out else err


def redact_value(key: str, value: str) -> str:
    upper = key.upper()
    is_sensitive = any(token in upper for token in REDACT_KEYWORDS)
    if upper.endswith("KEY") or upper.endswith("_KEY") or "API_KEY" in upper:
        is_sensitive = True
    if is_sensitive:
        if not value:
            return ""
        if len(value) <= 8:
            return "***"
        return value[:3] + "***" + value[-3:]
    return value


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip().replace("\r", "")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = redact_value(key, value)
    return data


def collect_basic_info() -> dict[str, Any]:
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def collect_git_info(repo_root: Path) -> dict[str, Any]:
    rc1, head = run_cmd(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
    rc2, branch = run_cmd(["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"])
    rc3, status = run_cmd(["git", "-C", str(repo_root), "status", "--short"])
    return {
        "head": head if rc1 == 0 else "",
        "branch": branch if rc2 == 0 else "",
        "dirty": bool(status.strip()) if rc3 == 0 else True,
    }


def collect_docker_info() -> dict[str, Any]:
    rc_v, docker_v = run_cmd(["docker", "version", "--format", "{{json .}}"])
    rc_ps, docker_ps = run_cmd(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}"])
    containers: list[dict[str, str]] = []
    if rc_ps == 0 and docker_ps:
        for line in docker_ps.splitlines():
            parts = re.split(r"\t+", line, maxsplit=2)
            if len(parts) >= 3:
                containers.append({"name": parts[0], "image": parts[1], "status": parts[2]})
    return {
        "docker_version_raw": docker_v if rc_v == 0 else "",
        "containers": containers,
    }


def to_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Runtime Profile Snapshot")
    lines.append("")
    lines.append(f"- Generated: `{payload.get('generated_at', '')}`")
    basic = payload.get("basic", {}) if isinstance(payload.get("basic"), dict) else {}
    lines.append(f"- Hostname: `{basic.get('hostname', '')}`")
    lines.append(f"- Platform: `{basic.get('platform', '')}`")
    lines.append(f"- Python: `{basic.get('python_version', '')}`")
    lines.append("")

    git_info = payload.get("git", {}) if isinstance(payload.get("git"), dict) else {}
    lines.append("## Git")
    lines.append(f"- Branch: `{git_info.get('branch', '')}`")
    lines.append(f"- HEAD: `{git_info.get('head', '')}`")
    lines.append(f"- Dirty: `{git_info.get('dirty', '')}`")
    lines.append("")

    lines.append("## Env (Sanitized)")
    env = payload.get("env_sanitized", {}) if isinstance(payload.get("env_sanitized"), dict) else {}
    if env:
        for k in sorted(env.keys()):
            lines.append(f"- `{k}` = `{env[k]}`")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Docker Containers")
    docker = payload.get("docker", {}) if isinstance(payload.get("docker"), dict) else {}
    containers = docker.get("containers", []) if isinstance(docker.get("containers"), list) else []
    if containers:
        for c in containers:
            if isinstance(c, dict):
                lines.append(f"- `{c.get('name','')}` | `{c.get('image','')}` | `{c.get('status','')}`")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    env_path = resolve(repo_root, args.env_file)

    payload = {
        "generated_at": now_iso(),
        "repo_root": str(repo_root),
        "env_file": str(env_path),
        "basic": collect_basic_info(),
        "git": collect_git_info(repo_root),
        "env_sanitized": parse_env_file(env_path),
        "docker": collect_docker_info(),
    }

    output_json = resolve(repo_root, args.output_json)
    output_md = resolve(repo_root, args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(to_markdown(payload), encoding="utf-8")

    print(f"runtime profile snapshot generated: {output_json}")
    print(f"runtime profile snapshot markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
