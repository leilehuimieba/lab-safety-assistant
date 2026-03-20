from __future__ import annotations

import csv
from pathlib import Path

import pytest


import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from kb_traceability import (
    is_missing,
    analyze_traceability,
    infer_traceability_from_title,
    TRACEABILITY_FIELDS,
)


def write_kb(path: Path, rows: list[dict]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_kb_row(
    id: str = "KB-0001",
    source_type: str = "SOP",
    source_title: str = "测试文档",
    source_org: str = "测试机构",
    source_date: str = "2024-01-01",
    source_url: str = "",
    **kwargs,
) -> dict:
    row = {
        "id": id,
        "title": "测试标题",
        "category": "通用",
        "subcategory": "测试",
        "lab_type": "化学",
        "risk_level": "3",
        "hazard_types": "测试",
        "scenario": "测试场景",
        "question": "测试问题",
        "answer": "测试答案",
        "steps": "测试步骤",
        "ppe": "护目镜",
        "forbidden": "禁止测试",
        "disposal": "测试处置",
        "first_aid": "测试急救",
        "emergency": "测试应急",
        "legal_notes": "测试法律",
        "references": "测试参考",
        "source_type": source_type,
        "source_title": source_title,
        "source_org": source_org,
        "source_version": "v1.0",
        "source_date": source_date,
        "source_url": source_url,
        "last_updated": "2024-01-01",
        "reviewer": "测试员",
        "status": "draft",
        "tags": "测试",
        "language": "zh-CN",
    }
    row.update(kwargs)
    return row


class TestIsMissing:
    def test_empty_string(self) -> None:
        assert is_missing("") is True

    def test_whitespace_only(self) -> None:
        assert is_missing("   ") is True

    def test_placeholder_values(self) -> None:
        assert is_missing("待补充") is True
        assert is_missing("无") is True
        assert is_missing("暂无") is True

    def test_valid_value(self) -> None:
        assert is_missing("这是一个有效的值") is False
        assert is_missing("2024-01-01") is False


class TestInferTraceability:
    def test_infer_msds_from_chemical_name(self) -> None:
        result = infer_traceability_from_title("MSDS-乙醇安全技术说明书", "化学")
        assert result.get("source_type") == "MSDS"

    def test_infer_sop_from_title(self) -> None:
        result = infer_traceability_from_title("实验室通风柜使用SOP", "化学")
        assert result.get("source_type") == "SOP"

    def test_infer_emergency_plan(self) -> None:
        result = infer_traceability_from_title("化学灼伤应急处置", "应急")
        assert result.get("source_type") == "应急预案"

    def test_infer_system_from_category(self) -> None:
        result = infer_traceability_from_title("培训管理制度", "管理")
        assert result.get("source_type") == "制度"


class TestAnalyzeTraceability:
    def test_complete_entry(self, tmp_path: Path) -> None:
        kb_path = tmp_path / "knowledge_base_curated.csv"
        rows = [
            make_kb_row(
                id="KB-0001",
                source_type="SOP",
                source_title="测试SOP",
                source_org="测试机构",
                source_date="2024-01-01",
                source_url="https://example.com",
            )
        ]
        write_kb(kb_path, rows)

        report = analyze_traceability(kb_path)
        assert report.total == 1
        assert report.complete == 1
        assert report.incomplete == 0

    def test_incomplete_entry_missing_date(self, tmp_path: Path) -> None:
        kb_path = tmp_path / "knowledge_base_curated.csv"
        rows = [
            make_kb_row(
                id="KB-0001",
                source_type="SOP",
                source_title="测试SOP",
                source_org="测试机构",
                source_date="",  # Missing
                source_url="https://example.com",
            )
        ]
        write_kb(kb_path, rows)

        report = analyze_traceability(kb_path)
        assert report.total == 1
        assert report.complete == 0
        assert report.incomplete == 1
        assert len(report.missing_fields["source_date"]) == 1
