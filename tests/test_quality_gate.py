from __future__ import annotations

import csv
from pathlib import Path

import quality_gate as qg


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_kb_rows(count: int = 50) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(1, count + 1):
        row = {key: "" for key in qg.KB_FIELDNAMES}
        row["id"] = f"KB-{1000 + i}"
        row["title"] = f"title-{i}"
        row["category"] = "通用"
        row["question"] = f"question-{i}"
        row["answer"] = f"answer-{i}"
        row["risk_level"] = "3"
        row["language"] = "zh-CN"
        rows.append(row)
    return rows


def make_eval_rows(count: int = 30) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(1, count + 1):
        row = {key: "" for key in qg.EVAL_FIELDNAMES}
        row["id"] = f"EVAL-{i:04d}"
        row["domain"] = "化学"
        row["scenario"] = "测试"
        row["risk_level"] = "3"
        row["question"] = f"q-{i}"
        row["expected_keypoints"] = "A;B"
        row["expected_action"] = "动作"
        row["allowed_sources"] = "SOP"
        row["should_refuse"] = "no"
        row["evaluation_type"] = "qa"
        rows.append(row)
    return rows


def write_rules(path: Path, count: int = 10) -> None:
    lines = ["version: 1.0", "rules:"]
    for i in range(1, count + 1):
        lines.append(f"  - id: R-{i:03d}")
        lines.append("    category: test")
        lines.append("    match_type: keywords")
        lines.append("    patterns: [\"a\"]")
        lines.append("    action: safe_answer")
        lines.append("    severity: low")
        lines.append("    response: ok")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_checkers_pass_with_valid_minimal_repo(tmp_path: Path) -> None:
    write_csv(tmp_path / "knowledge_base_curated.csv", qg.KB_FIELDNAMES, make_kb_rows())
    write_csv(tmp_path / "eval_set_v1.csv", qg.EVAL_FIELDNAMES, make_eval_rows())
    write_rules(tmp_path / "safety_rules.yaml", count=10)

    errors: list[str] = []
    qg.check_kb(tmp_path, errors)
    qg.check_eval(tmp_path, errors)
    qg.check_rules(tmp_path, errors)
    assert errors == []


def test_check_eval_detects_duplicate_id(tmp_path: Path) -> None:
    write_csv(tmp_path / "knowledge_base_curated.csv", qg.KB_FIELDNAMES, make_kb_rows())
    rows = make_eval_rows()
    rows[1]["id"] = rows[0]["id"]
    write_csv(tmp_path / "eval_set_v1.csv", qg.EVAL_FIELDNAMES, rows)
    write_rules(tmp_path / "safety_rules.yaml", count=10)

    errors: list[str] = []
    qg.check_eval(tmp_path, errors)
    assert any("重复 id" in item for item in errors)


def test_check_eval_accepts_fuzzy_type(tmp_path: Path) -> None:
    write_csv(tmp_path / "knowledge_base_curated.csv", qg.KB_FIELDNAMES, make_kb_rows())
    rows = make_eval_rows()
    rows[0]["evaluation_type"] = "fuzzy"
    write_csv(tmp_path / "eval_set_v1.csv", qg.EVAL_FIELDNAMES, rows)
    write_rules(tmp_path / "safety_rules.yaml", count=10)

    errors: list[str] = []
    qg.check_eval(tmp_path, errors)
    assert all("evaluation_type" not in item for item in errors)
