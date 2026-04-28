"""项目路径常量，统一入口避免各脚本硬编码相对路径。"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPTS_DIR = REPO_ROOT / "scripts"
WEB_DEMO_DIR = REPO_ROOT / "web_demo"
TESTS_DIR = REPO_ROOT / "tests"
DOCS_DIR = REPO_ROOT / "docs"
DEPLOY_DIR = REPO_ROOT / "deploy"
DATA_SOURCES_DIR = REPO_ROOT / "data_sources"
MANUAL_SOURCES_DIR = REPO_ROOT / "manual_sources"
RELEASE_EXPORTS_DIR = REPO_ROOT / "release_exports"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
OUTPUT_DIR = REPO_ROOT / "output"
LOGS_DIR = REPO_ROOT / "logs"

KNOWLEDGE_BASE_CSV = REPO_ROOT / "knowledge_base_curated.csv"
SAFETY_RULES_YAML = REPO_ROOT / "safety_rules.yaml"
EVAL_SET_CSV = REPO_ROOT / "eval_set_v1.csv"
