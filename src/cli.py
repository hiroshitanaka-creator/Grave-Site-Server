import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Dict, List


KEYWORD_MOOD_MAP = {
    "嬉": "happiness",
    "楽": "joy",
    "達成": "accomplishment",
    "疲": "tired",
    "怒": "anger",
    "不安": "anxiety",
    "悲": "sadness",
    "寂": "loneliness",
    "感謝": "gratitude",
    "希望": "hope",
}

KEYWORD_TOPIC_MAP = {
    "仕事": "work",
    "会社": "work",
    "上司": "workplace",
    "勉強": "study",
    "学校": "school",
    "家族": "family",
    "友": "friendship",
    "恋": "relationship",
    "運動": "health",
    "体調": "health",
    "旅行": "travel",
    "趣味": "hobby",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="input.txt の日記を解析して output/ に CSV または JSON を保存します。"
    )
    parser.add_argument(
        "--input",
        default="input.txt",
        help="入力ファイルパス（デフォルト: input.txt）",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="json",
        help="出力フォーマット（csv または json）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="出力ファイル名（未指定時は output/diary_output.<format>）",
    )
    return parser.parse_args()


def generate_mood_tag(entry: str) -> str:
    for keyword, mood in KEYWORD_MOOD_MAP.items():
        if keyword in entry:
            return mood
    return "neutral"


def generate_topic_tag(entry: str) -> str:
    detected_topics = []
    for keyword, topic in KEYWORD_TOPIC_MAP.items():
        if keyword in entry and topic not in detected_topics:
            detected_topics.append(topic)

    if not detected_topics:
        return "daily-life"

    return ", ".join(detected_topics[:2])


def generate_summary(entry: str, max_length: int = 30) -> str:
    cleaned = entry.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1]}…"


def build_record(entry: str) -> Dict[str, str]:
    if not entry.strip():
        raise ValueError("空行は処理できません")

    return {
        "date": date.today().isoformat(),
        "entry": entry.strip(),
        "mood_tag": generate_mood_tag(entry),
        "topic_tag": generate_topic_tag(entry),
        "summary": generate_summary(entry),
    }


def save_csv(records: List[Dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "entry", "mood_tag", "topic_tag", "summary"],
        )
        writer.writeheader()
        writer.writerows(records)


def save_json(records: List[Dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"入力ファイルが見つかりません: {input_path}")
        return 1

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = args.output or f"diary_output.{args.format}"
    output_path = output_dir / output_name

    records: List[Dict[str, str]] = []
    processed_count = 0
    failed_count = 0

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw_entry = line.rstrip("\n")
            if not raw_entry.strip():
                continue

            processed_count += 1
            try:
                records.append(build_record(raw_entry))
            except Exception as exc:
                failed_count += 1
                print(f"行 {line_no} の処理に失敗しました: {exc}")

    if args.format == "csv":
        save_csv(records, output_path)
    else:
        save_json(records, output_path)

    print(f"出力完了: {output_path}")
    print(f"処理件数: {processed_count}")
    print(f"失敗件数: {failed_count}")
    print(f"保存件数: {len(records)}")

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
