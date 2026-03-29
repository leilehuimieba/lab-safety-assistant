#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def run_cmd(cmd: list[str]) -> CmdResult:
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return CmdResult(
        returncode=completed.returncode,
        stdout=(completed.stdout or "").strip(),
        stderr=(completed.stderr or "").strip(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fix Dify container host mapping for embedding endpoint "
            "(host.docker.internal -> fake embedding container IP)."
        )
    )
    parser.add_argument("--embed-container", default="fake-ollama", help="Embedding fallback container name.")
    parser.add_argument("--target-host", default="host.docker.internal", help="Host alias used in embedding config.")
    parser.add_argument("--target-port", type=int, default=11434, help="Embedding endpoint port.")
    parser.add_argument(
        "--containers",
        nargs="+",
        default=["docker-api-1", "docker-worker-1", "docker-plugin_daemon-1"],
        help="Containers to patch /etc/hosts in.",
    )
    parser.add_argument(
        "--preferred-network",
        default="docker_default",
        help="Preferred docker network when resolving embed container IP.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip post-patch curl verification inside each container.",
    )
    return parser.parse_args()


def pick_container_ip(networks: dict, preferred_network: str) -> str:
    preferred = networks.get(preferred_network) if isinstance(networks, dict) else None
    if isinstance(preferred, dict):
        ip = str(preferred.get("IPAddress") or "").strip()
        if ip:
            return ip

    if isinstance(networks, dict):
        for _, cfg in networks.items():
            if isinstance(cfg, dict):
                ip = str(cfg.get("IPAddress") or "").strip()
                if ip:
                    return ip
    return ""


def resolve_embed_ip(embed_container: str, preferred_network: str) -> str:
    result = run_cmd(["docker", "inspect", embed_container, "--format", "{{json .NetworkSettings.Networks}}"])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to inspect {embed_container}: {result.stderr or result.stdout}")
    try:
        networks = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid inspect output for {embed_container}: {result.stdout}") from exc
    ip = pick_container_ip(networks, preferred_network)
    if not ip:
        raise RuntimeError(f"Cannot resolve IP for {embed_container} from networks: {networks}")
    return ip


def patch_hosts(container: str, target_host: str, target_ip: str) -> None:
    ip_host_literal = f"{target_ip} {target_host}"
    ip_host = shlex.quote(ip_host_literal)
    regex = shlex.quote(f"^{target_ip}[[:space:]]+{target_host}$")
    script = (
        f"grep -Eq {regex} /etc/hosts || "
        f"echo {ip_host} >> /etc/hosts"
    )
    result = run_cmd(["docker", "exec", "-u", "0", container, "sh", "-lc", script])
    if result.returncode != 0:
        raise RuntimeError(f"Failed patch /etc/hosts in {container}: {result.stderr or result.stdout}")


def verify_endpoint(container: str, target_host: str, target_port: int) -> str:
    url = f"http://{target_host}:{target_port}/api/tags"
    result = run_cmd(["docker", "exec", container, "sh", "-lc", f"curl -sS -m 3 {shlex.quote(url)}"])
    if result.returncode != 0:
        raise RuntimeError(
            f"Verify failed in {container} for {url}: {result.stderr or result.stdout}"
        )
    return result.stdout


def main() -> int:
    args = parse_args()
    target_ip = resolve_embed_ip(args.embed_container, args.preferred_network)
    print(f"Resolved embedding IP: {args.embed_container} -> {target_ip}")

    for container in args.containers:
        patch_hosts(container=container, target_host=args.target_host, target_ip=target_ip)
        print(f"Patched: {container} /etc/hosts ({args.target_host} -> {target_ip})")

    if args.skip_verify:
        print("Skip verify enabled.")
        return 0

    for container in args.containers:
        body = verify_endpoint(container=container, target_host=args.target_host, target_port=args.target_port)
        preview = body[:160].replace("\n", " ")
        print(f"Verify OK: {container} -> {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
