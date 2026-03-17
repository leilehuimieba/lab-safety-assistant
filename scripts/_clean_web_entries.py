#!/usr/bin/env python3
"""
审查并清洗知识库中网页爬取条目的质量。
- 删除：纯导航页（WEB-005/008/013/018）及垃圾尾块（WEB-010-006）
- 修剪：去除 WEB-001 / WEB-010-001 / WEB-012-001 开头的导航行
- 标记：审查通过的条目 status 改为 reviewed
"""
import csv
import re
from pathlib import Path

KB_FIELDNAMES = [
    "id","title","category","subcategory","lab_type","risk_level","hazard_types",
    "scenario","question","answer","steps","ppe","forbidden","disposal",
    "first_aid","emergency","legal_notes","references","source_type",
    "source_title","source_org","source_version","source_date","source_url",
    "last_updated","reviewer","status","tags","language",
]

# 完全删除的条目 id（纯导航/无内容）
DELETE_IDS = {
    "WEB-005-001",  # 重庆大学：只有导航栏
    "WEB-008-001",  # 吉林大学：只有导航栏
    "WEB-013-001",  # 宁夏医科大学：只有导航栏
    "WEB-018-001",  # 重庆大学生物：只有导航栏
    "WEB-010-006",  # CERNET 末尾：新闻列表，与实验室安全无关
}

# 需要裁剪导航头的条目：{id: 保留从第几个中文字符密集段开始}
# 策略：删除开头连续的单行（1-6字）导航词，保留第一个实质性段落
TRIM_NAV_IDS = {
    "WEB-001-001",  # 南京林业大学：前两行是日期/标题重复
    "WEB-010-001",  # CERNET：前20行是网站导航
    "WEB-012-001",  # 上海交通大学：前~40行是网站导航
}


def is_nav_line(line: str) -> bool:
    """判断是否为导航噪声行：去空格后长度<=10 且不含句号/冒号等实质标点"""
    s = line.strip()
    if not s:
        return False
    if len(s) <= 10 and not re.search(r'[。；：:，,、（(【\d]', s):
        return True
    # 典型导航词
    NAV_WORDS = ['English', 'CERNET', '搜索', '关闭', '加入我们', '滚动', '每日要闻',
                 '前沿', '科普', '通知', '新闻', '专题', '人才', '评论', '资讯',
                 '中国教育', '下一代互联网', '高校科技', '教育信息化']
    if s in NAV_WORDS:
        return True
    return False


def trim_leading_nav(text: str) -> str:
    """去除文本开头连续的导航噪声行，保留第一个实质内容段落开始的内容"""
    lines = text.split('\n')
    # 找到第一个非导航行
    start = 0
    for i, line in enumerate(lines):
        if not is_nav_line(line):
            start = i
            break
    # 如果从 start 开始内容太短（<50字），尝试继续跳过
    result = '\n'.join(lines[start:]).strip()
    return result


def clean_answer(row_id: str, answer: str) -> str:
    if row_id in TRIM_NAV_IDS:
        return trim_leading_nav(answer)
    return answer


def main():
    csv_path = Path("knowledge_base_curated.csv")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    deleted = 0
    trimmed = 0
    marked_reviewed = 0

    cleaned_rows = []
    for row in rows:
        row_id = row["id"]

        # 1. 删除垃圾条目
        if row_id in DELETE_IDS:
            deleted += 1
            continue

        # 2. 清洗导航头
        if row_id in TRIM_NAV_IDS:
            original = row["answer"]
            cleaned = clean_answer(row_id, original)
            if cleaned != original:
                row["answer"] = cleaned
                trimmed += 1

        # 3. 将已审查的 WEB 条目标记为 reviewed（非垃圾、非 draft→reviewed）
        if row_id.startswith("WEB-") and row.get("status") == "draft":
            row["status"] = "reviewed"
            marked_reviewed += 1

        cleaned_rows.append(row)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=KB_FIELDNAMES)
        writer.writeheader()
        for row in cleaned_rows:
            writer.writerow({field: row.get(field, "") for field in KB_FIELDNAMES})

    print(f"Deleted:         {deleted} entries")
    print(f"Nav-trimmed:     {trimmed} entries")
    print(f"Marked reviewed: {marked_reviewed} entries")
    print(f"Total remaining: {len(cleaned_rows)}")


if __name__ == "__main__":
    main()
