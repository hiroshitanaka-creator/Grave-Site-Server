from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".csv", ".json"}


def load_records(path: Path) -> list[dict[str, Any]]:
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input file format: {path.suffix}")

    if extension == ".csv":
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    with path.open("r", encoding="utf-8") as json_file:
        payload = json.load(json_file)

    if not isinstance(payload, list):
        raise ValueError("JSON input must be an array of objects")
    return payload
