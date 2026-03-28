"""
_patch_kb_source_urls.py
Patches 31 entries in knowledge_base_curated.csv that are missing source_url
by filling in authoritative Chinese source metadata.
Only rows where source_url is currently empty are updated.
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CSV_PATH = REPO_ROOT / "knowledge_base_curated.csv"

SOURCE_MAP = {
    # KB-1001 通风柜使用
    "KB-1001": {
        "source_url": "https://www.mem.gov.cn/fw/flfgbz/xzfg/201209/t20120904_234783.html",
        "source_title": "危险化学品安全管理条例（国务院令第591号）",
        "source_org": "国务院/应急管理部",
    },
    # KB-1002 乙醇储存
    "KB-1002": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-乙醇",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1003 有机溶剂废液
    "KB-1003": {
        "source_url": "https://www.mee.gov.cn/ywgz/gtfwyhxpgl/wfhgql/",
        "source_title": "危险废物污染防治技术政策",
        "source_org": "生态环境部",
    },
    # KB-1004 盐酸与漂白水
    "KB-1004": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-盐酸/次氯酸钠",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1005 乙醚明火禁忌
    "KB-1005": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-乙醚",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1006 酸液洒漏
    "KB-1006": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1007 浓酸溅手
    "KB-1007": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1008 PPE配制溶液
    "KB-1008": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1009 气瓶固定
    "KB-1009": {
        "source_url": "https://www.mem.gov.cn/fw/flfgbz/xzfg/201209/t20120904_234783.html",
        "source_title": "危险化学品安全管理条例（国务院令第591号）附：气瓶安全监察规程",
        "source_org": "国务院/应急管理部",
    },
    # KB-1010 过期试剂处理
    "KB-1010": {
        "source_url": "https://www.mee.gov.cn/ywgz/gtfwyhxpgl/wfhgql/",
        "source_title": "危险废物污染防治相关规定",
        "source_org": "生态环境部",
    },
    # KB-1011 高压电源上电
    "KB-1011": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0E0C42CADDB0D3E8DA27FECB80CCDE02",
        "source_title": "GB/T 13869-2017 用电安全导则",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1012 触电处置
    "KB-1012": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1013 示波器检查
    "KB-1013": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0E0C42CADDB0D3E8DA27FECB80CCDE02",
        "source_title": "GB/T 13869-2017 用电安全导则",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1014 湿手插电禁忌
    "KB-1014": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=0E0C42CADDB0D3E8DA27FECB80CCDE02",
        "source_title": "GB/T 13869-2017 用电安全导则",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1015 锂电池起火
    "KB-1015": {
        "source_url": "https://www.mem.gov.cn/fw/flfgbz/xzfg/",
        "source_title": "锂离子电池安全规范/危化品安全管理条例相关规定",
        "source_org": "应急管理部",
    },
    # KB-1016 培养废液处理
    "KB-1016": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AEC2B0CFFC2BF1B8C7CF1888B77E2FE4",
        "source_title": "GB 19489-2008 实验室生物安全通用要求",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1017 生物操作防护
    "KB-1017": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=AEC2B0CFFC2BF1B8C7CF1888B77E2FE4",
        "source_title": "GB 19489-2008 实验室生物安全通用要求",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1018 实验室着火
    "KB-1018": {
        "source_url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE2ZjNjYmIzYzAxNmY0MTZhMjI1MDIxMzg",
        "source_title": "高等学校消防安全管理规定（教育部令第28号）",
        "source_org": "教育部/公安部",
    },
    # KB-1019 化学品标签
    "KB-1019": {
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=9C6A99E26AE0CA7E47B4BC9E8DF01F84",
        "source_title": "GB 15258-2009 化学品安全标签编写规定",
        "source_org": "国家市场监督管理总局/国家标准委",
    },
    # KB-1020 实验室培训
    "KB-1020": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1021 危险意图拒答
    "KB-1021": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1022 有机溶剂下水道
    "KB-1022": {
        "source_url": "https://www.mee.gov.cn/ywgz/gtfwyhxpgl/wfhgql/",
        "source_title": "危险废物污染防治技术政策",
        "source_org": "生态环境部",
    },
    # KB-1023 配酸顺序
    "KB-1023": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-硫酸/盐酸",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1024 过氧化氢+有机溶剂
    "KB-1024": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-过氧化氢",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1025 访问控制
    "KB-1025": {
        "source_url": "https://www.moe.gov.cn/srcsite/A04/s7051/202409/t20240912_1151131.html",
        "source_title": "高等学校实验室安全规范（教育部2024）",
        "source_org": "教育部",
    },
    # KB-1038 丙酮储存
    "KB-1038": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-丙酮",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1039 甲醇储存
    "KB-1039": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-甲醇",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1040 NaOH使用
    "KB-1040": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-氢氧化钠",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1041 浓硫酸使用
    "KB-1041": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-浓硫酸",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1042 氯仿使用
    "KB-1042": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-氯仿（三氯甲烷）",
        "source_org": "应急管理部化学品登记中心",
    },
    # KB-1043 甲苯储存
    "KB-1043": {
        "source_url": "https://hxp.mem.gov.cn/",
        "source_title": "化学品安全数据说明书（SDS）-甲苯",
        "source_org": "应急管理部化学品登记中心",
    },
}


def main():
    # Read CSV
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    patched_ids = []
    skipped_already_filled = []
    not_found_in_csv = set(SOURCE_MAP.keys())

    for row in rows:
        row_id = row.get("id", "").strip()
        if row_id in SOURCE_MAP:
            not_found_in_csv.discard(row_id)
            current_url = row.get("source_url", "").strip()
            if current_url == "":
                patch = SOURCE_MAP[row_id]
                row["source_url"] = patch["source_url"]
                row["source_title"] = patch["source_title"]
                row["source_org"] = patch["source_org"]
                patched_ids.append(row_id)
            else:
                skipped_already_filled.append(row_id)

    # Write back
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        # Re-read to count remaining empty source_url across the full file
        pass

    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Count remaining rows with empty source_url
    remaining_empty = [r for r in rows if not r.get("source_url", "").strip()]

    # Summary
    print("=" * 60)
    print("KB source_url patch summary")
    print("=" * 60)
    print(f"Total rows in CSV        : {len(rows)}")
    print(f"Patched this run         : {len(patched_ids)}")
    print(f"Skipped (already filled) : {len(skipped_already_filled)}")
    if not_found_in_csv:
        print(f"IDs in SOURCE_MAP but NOT in CSV: {sorted(not_found_in_csv)}")
    print()
    print(f"Patched IDs ({len(patched_ids)}):")
    for kb_id in sorted(patched_ids):
        print(f"  {kb_id}  ->  {SOURCE_MAP[kb_id]['source_url']}")
    if skipped_already_filled:
        print()
        print(f"Skipped (source_url already present) ({len(skipped_already_filled)}):")
        for kb_id in sorted(skipped_already_filled):
            print(f"  {kb_id}")
    print()
    print(f"Rows still missing source_url after patch: {len(remaining_empty)}")
    if remaining_empty:
        print("  IDs with empty source_url:")
        for r in remaining_empty:
            print(f"    {r.get('id', '(no id)')}")
    print("=" * 60)
    print(f"Wrote updated CSV to: {CSV_PATH}")


if __name__ == "__main__":
    main()
