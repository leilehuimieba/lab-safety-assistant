from __future__ import annotations

from pathlib import Path

import web_ingest_pipeline as wip


def test_resolve_skill_script_path_default_points_to_skill() -> None:
    path = wip.resolve_skill_script_path("")
    assert "skills" in str(path).lower()
    assert path.name == "fetch_web_content.py"


def test_load_skill_fetcher_module_from_temp_script(tmp_path: Path) -> None:
    script = tmp_path / "fetch_web_content.py"
    script.write_text(
        "class R:\n"
        "    def __init__(self):\n"
        "        self.status='ok'\n"
        "        self.provider='jina'\n"
        "        self.title='T'\n"
        "        self.content='正文内容'*100\n"
        "        self.quality_score=0.9\n"
        "        self.requires_auth=False\n"
        "        self.http_status=200\n"
        "        self.error_reason=''\n"
        "        self.fetched_at='2026-03-18T10:00:00+08:00'\n"
        "def fetch_with_fallback(url, providers, timeout, max_chars):\n"
        "    return R()\n",
        encoding="utf-8",
    )
    module = wip.load_skill_fetcher_module(script)
    assert module is not None
    result = module.fetch_with_fallback("https://example.com", ["jina"], 20, 30000)
    assert result.status == "ok"


def test_build_clean_documents_uses_skill_content_text() -> None:
    rows = [
        wip.SourceRow(
            source_id="WEB-001",
            title="测试来源",
            source_org="测试机构",
            category="化学",
            subcategory="制度",
            lab_type="化学实验室",
            risk_level="3",
            hazard_types="化学品",
            url="https://example.com/a",
            tags="测试",
            language="zh-CN",
            question_hint="测试问题",
        )
    ]
    fetch_results = [
        {
            "source_id": "WEB-001",
            "requested_url": "https://example.com/a",
            "final_url": "https://example.com/a",
            "status": "success",
            "provider": "jina",
            "quality_score": 0.88,
            "requires_auth": False,
            "fetched_at": "2026-03-18T10:00:00+08:00",
            "content_text": "实验室安全规范要求佩戴护目镜并检查通风柜。"
            * 20,
            "title": "页面标题",
        }
    ]
    docs = wip.build_clean_documents(rows, fetch_results)
    assert len(docs) == 1
    assert docs[0]["fetch_provider"] == "jina"
    assert docs[0]["source_title"] == "测试来源"

