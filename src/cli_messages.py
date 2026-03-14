from __future__ import annotations

from pathlib import Path

EMPTY_ENTRY_ERROR = "空行は処理できません"
INVALID_ENTRY_ERROR = "異常文字列は処理できません"
INVALID_DATE_ERROR = "--date は YYYY-MM-DD 形式で指定してください"


def format_input_file_not_found(path: Path) -> str:
    return f"入力ファイルが見つかりません: {path}"


def format_missing_calendar_id(env_name: str) -> str:
    return f"--calendar-id または環境変数 {env_name} を設定してください。"
