#!/usr/bin/env python3
"""
User Feedback Collector

This script manages the collection and analysis of user feedback on KB entries.
Feedback can be used to identify low-quality entries, improve answers, and
prioritize KB updates.

Feedback Types:
- thumbs_down: User indicated answer was unhelpful
- incorrect_info: User reported factual error
- missing_info: User indicated answer was incomplete
- hard_to_understand: User had difficulty understanding the answer
- other: Other feedback

Usage:
    python feedback_collector.py [command]

Commands:
    report      - Generate feedback analysis report
    export      - Export feedback as CSV for manual review
    stats       - Show feedback statistics
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


FEEDBACK_DIR = Path("artifacts/feedback")
FEEDBACK_FILE = FEEDBACK_DIR / "user_feedback.csv"


FEEDBACK_TYPES = {
    "thumbs_down",
    "incorrect_info",
    "missing_info",
    "hard_to_understand",
    "other"
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="User Feedback Collector")
    parser.add_argument(
        "--feedback-file",
        type=Path,
        default=FEEDBACK_FILE,
        help="Path to feedback CSV file"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    subparsers.add_parser("report", help="Generate feedback analysis report")
    subparsers.add_parser("export", help="Export feedback for manual review")
    subparsers.add_parser("stats", help="Show feedback statistics")

    add_parser = subparsers.add_parser("add", help="Add a feedback entry")
    add_parser.add_argument("--question-id", required=True, help="Question/KB entry ID")
    add_parser.add_argument("--feedback-type", required=True, help="Feedback type")
    add_parser.add_argument("--comment", default="", help="Optional comment")

    return parser.parse_args()


def ensure_feedback_dir() -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_FILE.exists():
        with FEEDBACK_FILE.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "question_id", "feedback_type", "comment"
            ])
            writer.writeheader()


def load_feedback(feedback_file: Path) -> list[dict]:
    if not feedback_file.exists():
        return []
    
    with feedback_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def add_feedback(question_id: str, feedback_type: str, comment: str = "") -> bool:
    if feedback_type not in FEEDBACK_TYPES:
        print(f"Error: Invalid feedback type '{feedback_type}'")
        print(f"Valid types: {', '.join(sorted(FEEDBACK_TYPES))}")
        return False

    ensure_feedback_dir()

    with FEEDBACK_FILE.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "question_id", "feedback_type", "comment"
        ])
        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "question_id": question_id,
            "feedback_type": feedback_type,
            "comment": comment
        })

    print(f"Added feedback for {question_id}: {feedback_type}")
    return True


def analyze_feedback(feedback_list: list[dict]) -> dict:
    total = len(feedback_list)
    if total == 0:
        return {"total": 0}

    by_type = defaultdict(int)
    by_question = defaultdict(lambda: defaultdict(int))
    questions = set()

    for entry in feedback_list:
        fb_type = entry.get("feedback_type", "")
        qid = entry.get("question_id", "")
        questions.add(qid)
        by_type[fb_type] += 1
        by_question[qid][fb_type] += 1

    problematic_questions = []
    for qid, types in by_question.items():
        if sum(types.values()) >= 2:
            problematic_questions.append((qid, sum(types.values()), types))

    problematic_questions.sort(key=lambda x: -x[1])

    return {
        "total": total,
        "unique_questions": len(questions),
        "by_type": dict(by_type),
        "problematic_questions": problematic_questions[:10]
    }


def show_stats(feedback_list: list[dict]) -> None:
    analysis = analyze_feedback(feedback_list)

    print("=" * 60)
    print("User Feedback Statistics")
    print("=" * 60)
    print(f"Total feedback entries: {analysis['total']}")
    print(f"Unique questions: {analysis['unique_questions']}")

    if analysis["total"] > 0:
        print("\nFeedback by type:")
        for fb_type, count in sorted(analysis["by_type"].items()):
            pct = 100 * count / analysis["total"]
            print(f"  {fb_type}: {count} ({pct:.1f}%)")

        print("\nTop problematic questions (2+ feedback):")
        for qid, count, types in analysis["problematic_questions"][:5]:
            print(f"  {qid}: {count} feedback - {dict(types)}")
    else:
        print("\nNo feedback collected yet.")


def generate_report(feedback_list: list[dict]) -> None:
    analysis = analyze_feedback(feedback_list)

    report_path = FEEDBACK_DIR / f"feedback_report_{datetime.now().strftime('%Y%m%d')}.md"
    
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# User Feedback Analysis Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Summary Statistics\n\n")
        f.write(f"- Total feedback entries: {analysis['total']}\n")
        f.write(f"- Unique questions: {analysis['unique_questions']}\n\n")

        if analysis["total"] > 0:
            f.write("## Feedback by Type\n\n")
            for fb_type, count in sorted(analysis["by_type"].items()):
                pct = 100 * count / analysis["total"]
                f.write(f"- {fb_type}: {count} ({pct:.1f}%)\n")

            f.write("\n## Problematic Questions (Require Review)\n\n")
            f.write("| Question ID | Feedback Count | Types |\n")
            f.write("|------------|----------------|-------|\n")
            for qid, count, types in analysis["problematic_questions"]:
                type_str = ", ".join(f"{k}:{v}" for k, v in types.items())
                f.write(f"| {qid} | {count} | {type_str} |\n")

            f.write("\n## Recommendations\n\n")
            if analysis["problematic_questions"]:
                f.write("1. Review the above questions with 2+ negative feedback\n")
                f.write("2. Update KB entries based on user-reported issues\n")
                f.write("3. Prioritize 'incorrect_info' and 'thumbs_down' feedback\n")
        else:
            f.write("No feedback collected yet.\n")

    print(f"Report generated: {report_path}")


def export_for_review(feedback_list: list[dict]) -> None:
    export_path = FEEDBACK_DIR / f"feedback_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    with export_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["question_id", "feedback_count", "thumbs_down", "incorrect_info", "missing_info", "hard_to_understand", "other"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        by_question = defaultdict(lambda: defaultdict(int))
        for entry in feedback_list:
            qid = entry.get("question_id", "")
            fb_type = entry.get("feedback_type", "")
            by_question[qid][fb_type] += 1

        for qid, types in sorted(by_question.items()):
            writer.writerow({
                "question_id": qid,
                "feedback_count": sum(types.values()),
                "thumbs_down": types.get("thumbs_down", 0),
                "incorrect_info": types.get("incorrect_info", 0),
                "missing_info": types.get("missing_info", 0),
                "hard_to_understand": types.get("hard_to_understand", 0),
                "other": types.get("other", 0)
            })

    print(f"Exported {len(by_question)} questions to: {export_path}")


def main() -> int:
    args = parse_args()
    feedback_file = args.feedback_file

    if args.command == "add":
        success = add_feedback(args.question_id, args.feedback_type, args.comment)
        return 0 if success else 1

    feedback_list = load_feedback(feedback_file)

    if args.command == "stats":
        show_stats(feedback_list)
    elif args.command == "report":
        generate_report(feedback_list)
    elif args.command == "export":
        export_for_review(feedback_list)
    else:
        print("Usage: python feedback_collector.py [stats|report|export|add]")
        print("\nCommands:")
        print("  stats   - Show feedback statistics")
        print("  report  - Generate analysis report")
        print("  export  - Export as CSV for manual review")
        print("  add     - Add a feedback entry (requires --question-id, --feedback-type, --comment)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
