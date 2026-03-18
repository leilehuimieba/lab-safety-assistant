from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_skill_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "skills" / "web-content-fetcher" / "scripts" / "fetch_web_content.py"
    spec = importlib.util.spec_from_file_location("skill_fetch_web_content", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_normalize_url_adds_scheme() -> None:
    mod = load_skill_module()
    assert mod.normalize_url("example.com/a") == "https://example.com/a"
    assert mod.normalize_url("http://example.com") == "http://example.com"


def test_route_providers_for_wechat_prefers_scrapling() -> None:
    mod = load_skill_module()
    providers = mod.route_providers(
        "https://mp.weixin.qq.com/s/abc",
        ["jina", "scrapling", "direct"],
    )
    assert providers[0] == "scrapling"


def test_quality_score_for_empty_and_normal_text() -> None:
    mod = load_skill_module()
    assert mod.quality_score("") == 0.0
    score = mod.quality_score("这是一个测试句子。它有两个句号。")
    assert 0.0 < score <= 1.0
