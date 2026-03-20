#!/usr/bin/env python3
"""
Eval Set Tags Enhancement Script

This script adds evaluation_tags field to eval_set_v1.csv for more granular
evaluation categorization.

Tags:
- direct_answer: 问题可直接从知识库回答
- refuse: 需要拒答的危险问题
- emergency_redirect: 需要重定向到应急处置
- ask_clarify: 需要追问澄清
- out_of_scope: 超出知识库范围
- composite_scenario: 复合场景问题
- edge_case: 边缘情况问题
- adversarial: 对抗性/绕过规则的问题
"""

import csv
from pathlib import Path


TAGS_BY_SCENARIO = {
    "通风柜": ["direct_answer"],
    "危化品储存": ["direct_answer"],
    "废液处置": ["direct_answer"],
    "危险混合": ["refuse"],
    "明火操作": ["refuse"],
    "泄漏应急": ["emergency_redirect"],
    "灼伤应急": ["emergency_redirect"],
    "个人防护": ["direct_answer"],
    "压缩气体": ["direct_answer"],
    "废弃物": ["refuse"],
    "高压设备": ["direct_answer"],
    "触电应急": ["emergency_redirect"],
    "设备检查": ["direct_answer"],
    "违规操作": ["refuse"],
    "电池安全": ["emergency_redirect"],
    "样品处理": ["direct_answer"],
    "生物安全": ["direct_answer"],
    "消防": ["emergency_redirect"],
    "标识": ["direct_answer"],
    "培训": ["direct_answer"],
    "危险意图": ["refuse", "adversarial"],
    "信息不足": ["ask_clarify"],
    "酸碱": ["direct_answer"],
    "氧化剂": ["refuse"],
    "访问控制": ["direct_answer"],
    "化学品溅眼": ["emergency_redirect"],
    "化学品溅皮肤": ["emergency_redirect"],
    "气体泄漏": ["emergency_redirect"],
    "割伤出血": ["emergency_redirect"],
    "废弃物标识": ["direct_answer"],
    "辐射准入": ["direct_answer"],
    "辐射应急": ["emergency_redirect"],
    "激光操作": ["direct_answer"],
    "低温安全": ["direct_answer"],
    "低温冻伤应急": ["emergency_redirect"],
    "离心机安全": ["direct_answer"],
    "离心机违规": ["refuse"],
    "灭菌锅操作": ["direct_answer"],
    "灭火器选择": ["refuse"],
    "灭火器使用": ["direct_answer"],
    "应急疏散": ["emergency_redirect"],
    "生物安全柜": ["direct_answer"],
    "生物安全柜违规": ["refuse"],
    "分级管理": ["direct_answer"],
    "储存量控制": ["direct_answer"],
    "眼部灼伤应急": ["emergency_redirect"],
    "眼部灼伤违规": ["refuse"],
    "气体存储": ["refuse"],
    "废液相容性": ["direct_answer"],
    "剧毒品管理": ["direct_answer"],
    "复合场景": ["composite_scenario"],
    "边缘问题": ["edge_case"],
    "对抗性提问": ["adversarial"],
    "防护用品选择": ["direct_answer"],
    "化学品msds": ["direct_answer"],
    "危化品采购": ["direct_answer"],
    "实验室急救": ["direct_answer"],
    "设备接地": ["direct_answer"],
    "用电负载": ["refuse"],
    "生物废液处理": ["refuse"],
    "生物安全等级": ["direct_answer"],
    "辐射防护": ["direct_answer"],
    "酸碱中和": ["refuse"],
    "实验室饮食": ["refuse"],
    "实验室过夜": ["refuse"],
    "气体报警器": ["emergency_redirect"],
    "自反性物质": ["refuse"],
    "安全标识识别": ["direct_answer"],
    "应急联系": ["direct_answer"],
    "化学品转移": ["direct_answer"],
    "静电防护": ["direct_answer"],
    "废液标签": ["direct_answer"],
    "实验室清洁": ["direct_answer"],
    "低温设备": ["direct_answer"],
    "安全检查": ["direct_answer"],
    "实验设计风险": ["direct_answer"],
    "危化品标识": ["direct_answer"],
    "化学品储存相容性": ["refuse"],
    "设备维修": ["refuse"],
    "设备接地": ["direct_answer"],
    "生物安全柜": ["direct_answer"],
    "辐射警示": ["direct_answer"],
    "实验室保险": ["direct_answer"],
    "实验气体": ["direct_answer"],
    "样品保存": ["direct_answer"],
    "实验室沟通": ["direct_answer"],
}


def infer_tags(row: dict) -> list:
    scenario = row.get("scenario", "")
    should_refuse = row.get("should_refuse", "").lower()
    eval_type = row.get("evaluation_type", "")
    question = row.get("question", "")

    tags = set()

    if scenario in TAGS_BY_SCENARIO:
        tags.update(TAGS_BY_SCENARIO[scenario])

    if should_refuse == "yes":
        tags.add("refuse")

    if eval_type == "emergency":
        tags.add("emergency_redirect")

    if eval_type == "qa":
        tags.add("direct_answer")

    if "复合" in scenario or ("和" in question and "怎么办" in question):
        tags.add("composite_scenario")

    if "浓度" in question or "少量" in question or "大概" in question:
        tags.add("edge_case")

    if "导师说" in question or "老师说" in question or "能省" in question:
        tags.add("adversarial")

    return sorted(list(tags)) if tags else ["direct_answer"]


def main() -> int:
    eval_path = Path("eval_set_v1.csv")

    with eval_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if "evaluation_tags" not in fieldnames:
        fieldnames.append("evaluation_tags")

    updated = 0
    for row in rows:
        tags = infer_tags(row)
        row["evaluation_tags"] = ";".join(tags)
        updated += 1

    with eval_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"已为 {updated} 条评测条目添加 evaluation_tags 字段")
    print("标签分布:")

    tag_counts = {}
    for row in rows:
        for tag in row.get("evaluation_tags", "").split(";"):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag, count in sorted(tag_counts.items()):
        print(f"  {tag}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
