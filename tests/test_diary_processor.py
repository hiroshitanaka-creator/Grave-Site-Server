from pathlib import Path

from src.diary_processor import (
    OUTPUT_COLUMNS,
    parse_entries,
    parse_text_block,
    process_entries,
    render_csv,
    render_json,
)


def test_normal_single_japanese_entry_has_expected_columns():
    text = "今日は会社で上司に怒られた。納得いかないけど、成長のチャンスと捉える。"
    parsed = parse_text_block(text)

    assert parsed.errors == []
    records = process_entries(parsed.entries, today="2026-02-06")

    assert len(records) == 1
    row = records[0]
    assert list(row.keys()) == OUTPUT_COLUMNS
    assert row["entry"] == text
    assert all(row[column] for column in OUTPUT_COLUMNS)


def test_multiple_entries_keeps_count_and_order():
    entries = [
        "朝は読書して気分がよかった。",
        "午後は会議が長引いて少し疲れた。",
        "夜は運動してリフレッシュした。",
    ]

    records = process_entries(entries, today="2026-02-07")

    assert len(records) == len(entries)
    assert [record["entry"] for record in records] == entries


def test_empty_lines_and_invalid_input_handling():
    raw_items = ["  ", "有効な日記", 123, None, "\n", "次の有効な日記"]

    parsed = parse_entries(raw_items)

    assert parsed.entries == ["有効な日記", "次の有効な日記"]
    assert len(parsed.errors) == 4
    assert "empty line" in parsed.errors[0]
    assert "invalid type=int" in parsed.errors[1]


def test_golden_file_csv_json_output():
    fixture_dir = Path(__file__).parent / "golden"
    input_text = (fixture_dir / "known_input.txt").read_text(encoding="utf-8")

    parsed = parse_text_block(input_text)
    records = process_entries(parsed.entries, today="2026-02-06")

    actual_csv = render_csv(records)
    actual_json = render_json(records)

    expected_csv = (fixture_dir / "expected_output.csv").read_text(encoding="utf-8")
    expected_json = (fixture_dir / "expected_output.json").read_text(encoding="utf-8")

    assert actual_csv == expected_csv
    assert actual_json == expected_json
