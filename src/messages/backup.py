"""Non-overwriting consistent SQLite backup; never uploads or delivers records."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def backup(source: Path, destination: Path) -> int:
    source, destination = source.resolve(), destination.resolve()
    # Read-only open must not create an empty database when the source path is wrong.
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
        original.execute("SELECT count(*) FROM messages").fetchone()
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with closing(sqlite3.connect(destination)) as copy:
                original.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
                return copy.execute("SELECT count(*) FROM messages").fetchone()[0]
        except BaseException:
            destination.unlink(missing_ok=True)
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        count = backup(args.source, args.destination)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": "Backup failed; existing files were not overwritten",
                }
            )
        )
        return 1
    print(json.dumps({"backed_up_records": count, "integrity": "ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
