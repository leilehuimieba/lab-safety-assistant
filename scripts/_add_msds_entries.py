#!/usr/bin/env python3
"""补充常见化学品 MSDS 知识库条目：丙酮、甲醇、NaOH、浓硫酸、氯仿、甲苯。"""
import csv
from pathlib import Path

KB_FIELDNAMES = [
    "id","title","category","subcategory","lab_type","risk_level","hazard_types",
    "scenario","question","answer","steps","ppe","forbidden","disposal",
    "first_aid","emergency","legal_notes","references","source_type",
    "source_title","source_org","source_version","source_date","source_url",
    "last_updated","reviewer","status","tags","language",
]

new_entries = [
    {
        "id": "KB-1038", "title": "危化品-丙酮储存与使用", "category": "危化品",
        "subcategory": "MSDS", "lab_type": "化学", "risk_level": "3",
        "hazard_types": "易燃;挥发性;麻醉性", "scenario": "丙酮（acetone）的安全使用与储存",
        "question": "丙酮应如何安全储存和使用？",
        "answer": "丙酮（CAS 67-64-1）是极易燃液体，沸点56°C，蒸气与空气可形成爆炸性混合物，闪点-18°C。储存于防火安全柜，远离热源、明火和氧化剂，容器密闭并在阴凉通风处存放。使用时必须在通风柜内操作，避免明火和静电；大量使用须做好防静电接地。吸入高浓度蒸气会引起头痛、眩晕，皮肤长期接触可致脱脂。废液收入有机废液桶，不得倒入下水道。",
        "steps": "确认通风柜开启;确认无明火和热源;防静电接地;密闭操作;废液入有机废液桶",
        "ppe": "护目镜;实验服;丁腈手套;通风柜内操作",
        "forbidden": "禁止明火加热;禁止与强氧化剂接触;禁止倒入下水道",
        "disposal": "有机废液桶，标注（含酮类）",
        "first_aid": "皮肤接触：大量清水冲洗。眼部：大量清水冲洗15分钟，就医。吸入：移至通风处，不适就医",
        "emergency": "大量泄漏立即切断火源，撤离人员，按化学品泄漏应急预案处理",
        "legal_notes": "遵守《危险化学品安全管理条例》",
        "references": "丙酮MSDS（GB/T 16483）;高校实验室危化品管理制度",
        "source_type": "MSDS", "source_title": "丙酮安全技术说明书",
        "source_org": "高校通用", "source_version": "2023",
        "source_date": "2023-01-01", "source_url": "",
        "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
        "tags": "丙酮;acetone;易燃;有机溶剂", "language": "zh-CN",
    },
    {
        "id": "KB-1039", "title": "危化品-甲醇储存与使用", "category": "危化品",
        "subcategory": "MSDS", "lab_type": "化学", "risk_level": "4",
        "hazard_types": "易燃;有毒;神经毒性", "scenario": "甲醇（methanol）的安全使用与储存",
        "question": "甲醇有什么特别的危险性需要注意？",
        "answer": "甲醇（CAS 67-56-1）是高毒易燃液体，对人体神经和视神经有严重损害：少量摄入（10mL）即可导致失明，摄入30mL可致死。蒸气吸入亦有毒性。储存于防火安全柜，远离热源和氧化剂。使用时须在通风柜内操作，严格佩戴PPE。甲醇容易与乙醇混淆，使用前务必确认标签。皮肤吸收也有危险，接触后立即冲洗。废液入有机废液桶并明确标注（甲醇）。",
        "steps": "核对标签确认为甲醇;确认通风柜开启;佩戴防护手套;在通风柜内操作;废液专桶收集",
        "ppe": "护目镜;防渗透手套（丁腈或氯丁橡胶）;实验服;通风柜内操作",
        "forbidden": "禁止明火;禁止误食或吸入蒸气;禁止与乙醇混用不贴标签",
        "disposal": "有机废液桶，标注（含甲醇/高毒）",
        "first_aid": "皮肤：大量清水冲洗。眼部：冲洗15分钟就医。吸入：移至通风处就医。误食：立即就医（视为中毒急救）",
        "emergency": "误食立即拨打120，告知甲醇摄入；大量泄漏按应急预案处理",
        "legal_notes": "甲醇属高毒物质，需进行双人双锁管理（部分单位要求），遵守《危险化学品安全管理条例》",
        "references": "甲醇MSDS（GB/T 16483）;高校实验室高毒化学品管理",
        "source_type": "MSDS", "source_title": "甲醇安全技术说明书",
        "source_org": "高校通用", "source_version": "2023",
        "source_date": "2023-01-01", "source_url": "",
        "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
        "tags": "甲醇;methanol;高毒;易燃;失明", "language": "zh-CN",
    },
    {
        "id": "KB-1040", "title": "危化品-氢氧化钠（NaOH）使用", "category": "危化品",
        "subcategory": "MSDS", "lab_type": "化学", "risk_level": "3",
        "hazard_types": "腐蚀性;强碱", "scenario": "NaOH（烧碱/强碱）的安全使用与配制",
        "question": "配制NaOH溶液有什么安全注意事项？",
        "answer": "氢氧化钠（NaOH，CAS 1310-73-2）为强腐蚀性固体，溶于水时大量放热。配制溶液时须先加水后缓慢加入NaOH固体，绝不能将水加入NaOH（防止剧烈飞溅）。操作时佩戴防碱护目镜、防化手套和实验服，在通风柜内或开阔通风处进行。NaOH对眼部腐蚀危险尤为严重，接触立即用大量清水冲洗至少15分钟并就医。避免皮肤接触，接触后立即用流水冲洗。储存于密闭容器，防止吸潮和CO2。",
        "steps": "佩戴PPE;先加水再加NaOH;缓慢添加并搅拌控温;容器做好标识;废液按碱性废液处理",
        "ppe": "防碱护目镜或面罩;丁腈手套;实验服",
        "forbidden": "禁止将水加入NaOH;禁止徒手操作;禁止与酸剧烈混合",
        "disposal": "稀释后按无机碱废液处理，pH调至中性后可按规定排放",
        "first_aid": "皮肤：大量清水冲洗20分钟。眼部：用洗眼器大量清水冲洗至少15分钟，立即就医",
        "emergency": "大量溅洒启动应急预案，佩戴PPE处理",
        "legal_notes": "遵守《危险化学品安全管理条例》",
        "references": "NaOH MSDS（GB/T 16483）;高校实验室化学品安全管理细则",
        "source_type": "MSDS", "source_title": "氢氧化钠安全技术说明书",
        "source_org": "高校通用", "source_version": "2023",
        "source_date": "2023-01-01", "source_url": "",
        "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
        "tags": "NaOH;氢氧化钠;强碱;腐蚀性;烧碱", "language": "zh-CN",
    },
    {
        "id": "KB-1041", "title": "危化品-浓硫酸使用", "category": "危化品",
        "subcategory": "MSDS", "lab_type": "化学", "risk_level": "4",
        "hazard_types": "腐蚀性;强酸;氧化性;放热", "scenario": "浓硫酸的安全使用与稀释",
        "question": "稀释浓硫酸时为什么要将酸缓慢加入水中，而不是相反？",
        "answer": "浓硫酸（H2SO4 >98%，CAS 7664-93-9）稀释时产生大量热，若将水加入浓硫酸，会使溶液局部剧烈沸腾，导致酸液飞溅，造成严重灼伤。正确操作：必须将浓硫酸缓慢地沿容器壁倒入水中（酸入水），同时搅拌散热。操作前确认通风良好，佩戴防酸护目镜和防化手套。浓硫酸有强腐蚀性，接触皮肤应立即用大量清水冲洗（不少于20分钟），眼部接触用洗眼器冲洗后立即就医。储存于阴凉干燥处，远离有机物和还原剂。",
        "steps": "佩戴防酸PPE;先在容器中加水;将浓硫酸缓慢沿壁倒入水中;搅拌控温;标识清楚",
        "ppe": "防酸护目镜或面罩;耐酸手套（厚丁腈或氯丁橡胶）;实验服",
        "forbidden": "禁止将水加入浓硫酸;禁止快速混合;禁止与有机物同存",
        "disposal": "酸性废液桶；需中和后处理",
        "first_aid": "皮肤：立即大量清水冲洗20分钟。眼部：洗眼器冲洗至少15分钟，立即就医",
        "emergency": "大量泄漏立即隔离，佩戴防酸PPE用沙土吸附，按应急预案处理",
        "legal_notes": "遵守《危险化学品安全管理条例》；浓硫酸属管控化学品，购买需审批",
        "references": "浓硫酸MSDS（GB/T 16483）;配酸SOP;高校化学品安全细则",
        "source_type": "MSDS", "source_title": "硫酸安全技术说明书",
        "source_org": "高校通用", "source_version": "2023",
        "source_date": "2023-01-01", "source_url": "",
        "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
        "tags": "浓硫酸;H2SO4;强酸;腐蚀性;稀释", "language": "zh-CN",
    },
    {
        "id": "KB-1042", "title": "危化品-氯仿使用", "category": "危化品",
        "subcategory": "MSDS", "lab_type": "化学", "risk_level": "4",
        "hazard_types": "有毒;致癌嫌疑;麻醉性;挥发性", "scenario": "氯仿（三氯甲烷）的安全使用",
        "question": "使用氯仿（三氯甲烷）有哪些特殊风险？",
        "answer": "氯仿（CHCl3，CAS 67-66-3）是常见有机溶剂，但具有潜在致癌性（IARC 2B类），长期暴露有肝肾损伤风险，吸入高浓度会引起麻醉。所有操作必须在通风柜内进行，不得在柜外开盖、倾倒或转移。氯仿会缓慢氧化生成光气（剧毒），因此须在阴凉避光处储存，避免与铝、镁、强碱接触。接触后皮肤立即清洗，不适立即就医并说明接触的化学品。废液入卤代烃废液桶（不得与非卤代废液混合）。",
        "steps": "确认通风柜开启;避光操作;密闭容器;废液入卤代烃废液桶",
        "ppe": "护目镜;丁腈手套;实验服;通风柜内操作",
        "forbidden": "禁止在柜外操作;禁止与铝/镁/强碱接触;禁止混入非卤代废液",
        "disposal": "卤代烃废液桶，标注（含氯仿）",
        "first_aid": "皮肤：清水冲洗。眼部：清水冲洗15分钟就医。吸入：移至通风处，有不适立即就医",
        "emergency": "大量泄漏立即撤离，通风，按应急预案处理",
        "legal_notes": "氯仿属IARC 2B类可疑致癌物；遵守危化品管理条例",
        "references": "氯仿MSDS（GB/T 16483）;IARC致癌物分类",
        "source_type": "MSDS", "source_title": "三氯甲烷安全技术说明书",
        "source_org": "高校通用", "source_version": "2023",
        "source_date": "2023-01-01", "source_url": "",
        "last_updated": "2026-03-15", "reviewer": "", "status": "draft",
        "tags": "氯仿;三氯甲烷;chloroform;致癌;卤代烃", "language": "zh-CN",
    },
]

csv_path = Path("knowledge_base_curated.csv")
with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

existing_ids = {r["id"] for r in rows}
added = 0
for entry in new_entries:
    if entry["id"] not in existing_ids:
        rows.append({field: entry.get(field, "") for field in KB_FIELDNAMES})
        existing_ids.add(entry["id"])
        added += 1

with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=KB_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in KB_FIELDNAMES})

print(f"Added {added} MSDS entries. Total: {len(rows)}")
