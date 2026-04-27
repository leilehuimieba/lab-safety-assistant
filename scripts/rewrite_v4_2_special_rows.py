#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

import ai_review_kb as ark


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply strict structured rewrite templates for V4.2 special rows."
    )
    parser.add_argument(
        "--input-csv",
        default="artifacts/relink_v4_2/relink_success_kb_candidates.csv",
        help="Input CSV with V4.2 relink-success rows.",
    )
    parser.add_argument(
        "--output-csv",
        default="artifacts/relink_v4_2/relink_success_kb_candidates_structured.csv",
        help="Output CSV after strict template rewrite.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ark.KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ark.KB_FIELDNAMES})


def append_token(raw: str, token: str) -> str:
    items = [item.strip() for item in (raw or "").split(";") if item.strip()]
    if token not in items:
        items.append(token)
    return ";".join(items)


def rewrite_webv2_001(row: dict[str, str]) -> None:
    row["scenario"] = "高校如何按《高等学校实验室安全规范》建立可执行的实验室安全管理体系"
    row["question"] = "《高等学校实验室安全规范》落地执行时，学校层面的核心要求和操作要点是什么？"
    row["answer"] = (
        "依据教育部办公厅印发的《高等学校实验室安全规范》（教科信厅函〔2023〕5号），"
        "学校层面应建立“组织责任+制度流程+风险管控+应急处置”的闭环。"
        "重点包括：建立校-院-实验室-项目负责人四级责任体系；"
        "落实安全准入培训、危险源辨识与风险评估、隐患排查整改、应急演练与事故报告；"
        "对危化品、危险气体、生物因子、辐射及特种设备实行全过程管理。"
    )
    row["steps"] = (
        "1) 建组织：明确主管部门和二级单位职责，逐级签署责任书。"
        "2) 建制度：发布并年度更新培训准入、检查整改、危险源管控、应急报告制度。"
        "3) 做准入：高风险项目先评估后实施，形成可追溯记录。"
        "4) 做巡检：按“排查-整改-复核”闭环执行并留痕。"
        "5) 配资源：落实专兼职安全人员、经费和关键防护设施。"
        "6) 强应急：发生事件后按预案处置并按规定时限上报。"
    )
    row["ppe"] = "按实验风险配备实验服、手套、护目镜/面屏和必要的呼吸防护，并完成上岗培训。"
    row["forbidden"] = (
        "禁止未培训或未准入人员开展实验；禁止未评估项目直接实施；"
        "禁止危险化学品无台账领用、超量存放或违规处置。"
    )
    row["disposal"] = (
        "实验废物分类收集并规范标识，危险废物集中暂存后交有资质单位转运处置，"
        "不得混入生活垃圾或直接排放。"
    )
    row["first_aid"] = "出现暴露或伤害时立即停止实验，先冲洗/止血/隔离，再按流程转诊并报告。"
    row["emergency"] = "事故发生后立即启动预案，先控风险源，再组织疏散与警戒，同时完成首报和续报。"
    row["references"] = (
        "1) 教育部办公厅关于印发《高等学校实验室安全规范》的通知（教科信厅函〔2023〕5号） "
        "https://www.gov.cn/zhengce/zhengceku/2023-02/21/content_5742498.htm ; "
        "2) 附件PDF（高校镜像） "
        "https://lab.sicnu.edu.cn/upload/file/20260325/6391004610320021101947055.pdf"
    )
    row["source_title"] = "高等学校实验室安全规范（教科信厅函〔2023〕5号）"
    row["source_org"] = "教育部办公厅（中国政府网政策库）"
    row["source_url"] = "https://www.gov.cn/zhengce/zhengceku/2023-02/21/content_5742498.htm"
    row["source_type"] = "政策"
    row["language"] = "zh-CN"


def rewrite_webv2_012(row: dict[str, str]) -> None:
    row["scenario"] = "实验室如何依据 SDS 建立危化品使用前核验与应急控制流程"
    row["question"] = "SDS 在实验室中应如何查阅和使用，哪些关键章节必须在操作前确认？"
    row["answer"] = (
        "依据 CCOHS 的 WHMIS SDS 指南，SDS 是危化品操作前的必查文件。"
        "实验前至少应核验：第1节（产品与供应商）、第2节（危险性识别）、"
        "第4节（急救措施）、第5/6节（消防和泄漏处置）、"
        "第7/8节（操作储存与暴露控制）、第10节（稳定性）、"
        "第13节（废弃处置）和第16节（修订信息）。"
    )
    row["steps"] = (
        "1) 取SDS：按产品名称/货号获取最新版 SDS，并与容器标签逐项核对。"
        "2) 读关键节：操作前完成第1、2、4、5、6、7、8、10、13、16节核验。"
        "3) 转流程：把第4、5、6节转成现场急救卡和泄漏应急卡。"
        "4) 配PPE：按第8节要求和岗位风险评估确定防护组合。"
        "5) 做版本控：记录第16节修订日期，更新后同步修订SOP与培训材料。"
    )
    row["ppe"] = "按 SDS 第8节执行，常见包括手套、护目镜/面屏、防护服和呼吸防护。"
    row["forbidden"] = "禁止在未获取 SDS 或 SDS 与实物不一致时开展操作；禁止用经验替代 SDS 风险控制要求。"
    row["disposal"] = "按 SDS 第13节与本单位危废制度执行分类收集、标识、暂存与移交，禁止混倒。"
    row["first_aid"] = "发生暴露时按 SDS 第4节执行急救并及时就医。"
    row["emergency"] = "发生泄漏或起火时按 SDS 第5/6节处置，并同步启动单位应急预案。"
    row["references"] = (
        "WHMIS - Safety Data Sheet (SDS), CCOHS (Fact sheet revised 2025-06-02) "
        "https://www.ccohs.ca/oshanswers/chemicals/whmis_ghs/sds.pdf"
    )
    row["source_title"] = "WHMIS - Safety Data Sheet (SDS)"
    row["source_org"] = "Canadian Centre for Occupational Health and Safety (CCOHS)"
    row["source_url"] = "https://www.ccohs.ca/oshanswers/chemicals/whmis_ghs/sds.pdf"
    row["source_type"] = "SDS指南"
    row["language"] = "zh-CN"


def rewrite_webv3_002(row: dict[str, str]) -> None:
    row["title"] = "临床实验室生物安全指南（WS/T 442—2024）"
    row["scenario"] = "按 WS/T 442—2024 执行临床实验室人员防护与分区/气流组织"
    row["question"] = "依据 WS/T 442—2024，临床实验室在“人员防护”和“分区管理/气流组织”方面应如何执行？"
    row["risk_level"] = "4"
    row["answer"] = (
        "按 WS/T 442—2024 的可核验条款执行："
        "6.1.2 用于门禁与关键实验间门的自动关闭控制；"
        "6.1.15 用于病原标本操作区配置生物安全柜等隔离装置；"
        "6.2.3 与 6.2.4 用于定向气流、缓冲间与生物安全柜布置；"
        "B.3.5 用于个体防护装备正确选择和使用；"
        "B.3.8 用于气溶胶风险活动在生物安全柜内进行；"
        "D.2.6 用于高风险场景加强口罩、防护服、护目/面屏等防护。"
    )
    row["steps"] = (
        "1) 6.1.2：核查主入口门和生物安全柜实验间门可自动关闭。"
        "2) 6.1.15：确认病原标本操作区配备并实际使用生物安全柜等隔离装置。"
        "3) 6.2.3/6.2.4：核查缓冲间、定向气流、排风和生物安全柜布置是否达标。"
        "4) B.3.5 + D.2.6：建立按暴露风险选配 PPE 的岗位清单。"
        "5) B.3.8：将气溶胶风险操作统一纳入生物安全柜内并形成检查记录。"
    )
    row["ppe"] = (
        "按 B.3.5 和 D.2.6 执行：常规配置手套、口罩、护目镜/面屏、防护服；"
        "高风险场景加强医用防护口罩、防护服、护目/面屏和必要足部防护。"
    )
    row["forbidden"] = (
        "按附录B执行：禁止在实验区饮食、吸烟、处理隐形眼镜和存放食品/个人物品（B.3.3）；"
        "存在空气传播风险或可能产生气溶胶时，禁止在生物安全柜外操作（B.3.8）。"
    )
    row["disposal"] = "按 7.11 相关要求执行医疗废物分类、包装、转运和处置。"
    row["first_aid"] = "发生暴露时按附录C和本单位程序执行冲洗/消毒、报告和医学评估。"
    row["emergency"] = (
        "按 7.12.2 建立应急方案（组织、PPE、处置程序、报告和通讯）；"
        "溢洒、离心事故等场景按附录C执行区域控制、消毒与事件报告。"
    )
    row["references"] = (
        "1) 临床实验室生物安全指南（WS/T 442—2024）挂载页 "
        "https://wjw.nmg.gov.cn/zfxxgk/fdzzgknr/hybz/wsbz/202408/t20240815_2558602.html ; "
        "2) 规范PDF "
        "https://wjw.nmg.gov.cn/zfxxgk/fdzzgknr/hybz/wsbz/202408/P020240815584206907728.pdf"
    )
    row["source_title"] = "临床实验室生物安全指南（WS/T 442—2024）"
    row["source_org"] = "国家卫生健康委员会（内蒙古卫健委挂载）"
    row["source_url"] = "https://wjw.nmg.gov.cn/zfxxgk/fdzzgknr/hybz/wsbz/202408/P020240815584206907728.pdf"
    row["source_type"] = "标准"
    row["language"] = "zh-CN"


def apply_template(row: dict[str, str]) -> bool:
    row_id = (row.get("id") or "").strip()
    if row_id == "WEBV2-001-001":
        rewrite_webv2_001(row)
    elif row_id == "WEBV2-012-001":
        rewrite_webv2_012(row)
    elif row_id == "WEBV3-002-001":
        rewrite_webv3_002(row)
    else:
        return False

    row["status"] = "template_rewritten_v4_2"
    row["reviewer"] = "template-rewrite:v4_2_strict"
    row["last_updated"] = today_str()
    row["tags"] = append_token(row.get("tags", ""), "template_rewrite_v4_2")
    legal = (row.get("legal_notes") or "").strip()
    note = "[Template rewrite v4.2 strict fields: answer/steps/ppe/forbidden/emergency]"
    row["legal_notes"] = f"{legal} {note}".strip()
    return True


def normalize_row(raw: dict[str, str]) -> dict[str, str]:
    return {field: (raw.get(field) or "").strip() for field in ark.KB_FIELDNAMES}


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv).resolve()
    output_csv = Path(args.output_csv).resolve()

    if not input_csv.exists():
        raise SystemExit(f"Input CSV not found: {input_csv}")

    rows = read_rows(input_csv)
    rewritten = 0
    out_rows: list[dict[str, str]] = []

    for raw in rows:
        row = normalize_row(raw)
        if apply_template(row):
            rewritten += 1
        out_rows.append(row)

    write_rows(output_csv, out_rows)

    print("V4.2 strict template rewrite completed")
    print(f"- input: {input_csv}")
    print(f"- output: {output_csv}")
    print(f"- total_rows: {len(out_rows)}")
    print(f"- rewritten_rows: {rewritten}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
