from __future__ import annotations

from pathlib import Path

EMPTY_ENTRY_ERROR = "空行は処理できません"
INVALID_ENTRY_ERROR = "異常文字列は処理できません"


def format_input_file_not_found(path: Path) -> str:
    return f"入力ファイルが見つかりません: {path}"
