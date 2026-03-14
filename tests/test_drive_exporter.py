from __future__ import annotations

from datetime import date

import pytest

from src.exporters.drive_exporter import (
    DRIVE_FOLDER_ID_ENV,
    SERVICE_ACCOUNT_JSON_ENV,
    DriveExporterError,
    build_daily_filename,
    load_drive_config,
)


def test_build_daily_filename_uses_expected_convention():
    assert build_daily_filename(date(2026, 2, 6), "csv") == "diary_2026-02-06.csv"
    assert build_daily_filename(date(2026, 2, 6), ".json") == "diary_2026-02-06.json"


def test_build_daily_filename_rejects_unknown_extension():
    with pytest.raises(ValueError, match="extension は csv または json"):
        build_daily_filename(date(2026, 2, 6), "txt")


def test_load_drive_config_requires_service_account_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(SERVICE_ACCOUNT_JSON_ENV, raising=False)
    monkeypatch.setenv(DRIVE_FOLDER_ID_ENV, "folder-id")

    with pytest.raises(DriveExporterError, match=SERVICE_ACCOUNT_JSON_ENV):
        load_drive_config()


def test_load_drive_config_requires_existing_service_account_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setenv(SERVICE_ACCOUNT_JSON_ENV, str(missing_path))
    monkeypatch.setenv(DRIVE_FOLDER_ID_ENV, "folder-id")

    with pytest.raises(DriveExporterError, match="ファイルが見つかりません"):
        load_drive_config()


def test_load_drive_config_requires_folder_id(tmp_path, monkeypatch: pytest.MonkeyPatch):
    key_file = tmp_path / "sa.json"
    key_file.write_text("{}", encoding="utf-8")

    monkeypatch.setenv(SERVICE_ACCOUNT_JSON_ENV, str(key_file))
    monkeypatch.delenv(DRIVE_FOLDER_ID_ENV, raising=False)

    with pytest.raises(DriveExporterError, match=DRIVE_FOLDER_ID_ENV):
        load_drive_config()
