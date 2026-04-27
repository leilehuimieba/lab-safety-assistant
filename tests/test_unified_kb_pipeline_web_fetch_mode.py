from __future__ import annotations

import argparse
from pathlib import Path

import unified_kb_pipeline as ukp


def make_args() -> argparse.Namespace:
    return argparse.Namespace(
        web_manifest="data_sources\\web_seed_urls.csv",
        web_concurrency=3,
        web_max_chars=1200,
        web_overlap=120,
        web_fetcher_mode="auto",
        web_skill_script="",
        web_skill_providers="jina,scrapling,direct",
        web_fetch_timeout=20,
        web_fetch_max_chars=30000,
    )


def test_build_web_command_contains_fetch_mode_flags(tmp_path: Path) -> None:
    args = make_args()
    output_dir = tmp_path / "web_out"
    repo_root = Path("D:/workspace/lab-safe-assistant-github")
    cmd = ukp.build_web_command(args, output_dir=output_dir, repo_root=repo_root)
    assert "--fetcher-mode" in cmd
    assert "auto" in cmd
    assert "--skill-providers" in cmd
    assert "jina,scrapling,direct" in cmd


def test_build_web_command_appends_skill_script_when_set(tmp_path: Path) -> None:
    args = make_args()
    args.web_skill_script = "skills/web-content-fetcher/scripts/fetch_web_content.py"
    output_dir = tmp_path / "web_out"
    repo_root = Path("D:/workspace/lab-safe-assistant-github")
    cmd = ukp.build_web_command(args, output_dir=output_dir, repo_root=repo_root)
    assert "--web-skill-script" not in cmd
    assert "--skill-script" in cmd
    assert "skills/web-content-fetcher/scripts/fetch_web_content.py" in cmd

