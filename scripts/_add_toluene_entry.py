#!/usr/bin/env python3
"""补充甲苯（toluene）MSDS 知识库条目 KB-1043。"""
import csv
from pathlib import Path

KB_FIELDNAMES = [
    "id","title","category","subcategory","lab_type","risk_level","hazard_types",
    "scenario","question","answer","steps","ppe","forbidden","disposal",
    "first_aid","emergency","legal_notes","references","source_type",
    "source_title","source_org","source_version","source_date","source_url",
    "last_updated","reviewer","status","tags","language",
]

new_entry = {
    "id": "KB-1043", "title": "危化品-甲苯储存与使用", "category": "危化品",
    "subcategory": "MSDS", "lab_type": "化学", "risk_level": "3",
    "hazard_types": "易燃;挥发性;神经毒性",
    "scenario": "甲苯（toluene）的安全使用与储存",
    "question": "使用甲苯时需要注意哪些安全事项？",
    "answer": "甲苯（CAS 108-88-3）是常见有机溶剂，易燃（闪点4°C），具有神经毒性，长期吸入可损害中枢神经系统，引起头痛、眩晕、疲劳，大剂量暴露可致麻醉。与苯相比，甲苯无已知致癌性，但仍需严格防护。所有操作必须在通风柜内进行，严格佩戴PPE，避免明火和热源（沸点110.6°C，蒸气比空气重，可沿地面扩散至远处火源）。注意甲苯是良好的脂溶性溶剂，可经皮肤吸收，接触后立即冲洗。储存于防火安全柜，远离氧化剂和酸类，容器密闭阴凉存放。废液收入有机废液桶（非卤代）。",
    "steps": "确认通风柜开启;确认无明火和热源;防静电操作;密闭操作;废液入有机废液桶",
    "ppe": "护目镜;丁腈手套;实验服;通风柜内操作",
    "forbidden": "禁止明火加热;禁止在柜外长时间敞口操作;禁止倒入下水道",
    "disposal": "有机废液桶（非卤代，标注含甲苯）",
    "first_aid": "皮肤接触：大量清水冲洗。眼部：大量清水冲洗15分钟，就医。吸入：移至通风处，不适就医",
    "emergency": "大量泄漏立即切断火源，撤离人员，通风，按化学品泄漏应急预案处理",
    "legal_notes": "遵守《危险化学品安全管理条例》",
    "references": "甲苯MSDS（GB/T 16483）;高校实验室危化品管理制度",
    "source_type": "MSDS", "source_title": "甲苯安全技术说明书",
    "source_org": "高校通用", "source_version": "2023",
    "source_date": "2023-01-01", "source_url": "",
    "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
    "tags": "甲苯;toluene;易燃;有机溶剂;神经毒性", "language": "zh-CN",
}

csv_path = Path("knowledge_base_curated.csv")
with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

existing_ids = {r["id"] for r in rows}
if new_entry["id"] not in existing_ids:
    rows.append({field: new_entry.get(field, "") for field in KB_FIELDNAMES})
    added = 1
else:
    added = 0

with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=KB_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in KB_FIELDNAMES})

print(f"Added {added} entry. Total: {len(rows)}")
