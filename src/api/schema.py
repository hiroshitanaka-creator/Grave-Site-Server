"""Generate the Actions contract from the actual FastAPI application."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.api.main import app


def contract(server_url: str = "https://replace-with-your-api.example.invalid") -> dict:
    schema = app.openapi()
    return {**schema, "servers": [{"url": server_url}]}


def main() -> int:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("openapi/gpts_actions.yaml"))
    parser.add_argument("--server-url", default="https://replace-with-your-api.example.invalid")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(contract(args.server_url), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
