from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .pipeline import build_embedding_records, search_similar
from .storage import JsonEmbeddingStore, SQLiteEmbeddingStore


def _build_store(backend: str, output_path: Path):
    if backend == "json":
        return JsonEmbeddingStore(output_path)
    return SQLiteEmbeddingStore(output_path)


def cmd_index(args: argparse.Namespace) -> int:
    records = build_embedding_records(Path(args.input), dimensions=args.dimensions)
    store = _build_store(args.backend, Path(args.output))
    store.save(records)
    print(f"Indexed {len(records)} summary embeddings into {args.output} ({args.backend})")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = _build_store(args.backend, Path(args.store))
    records = store.load()
    if not records:
        print("No embeddings found. Run `index` first.", file=sys.stderr)
        return 1

    results = search_similar(
        query=args.query,
        records=records,
        dimensions=args.dimensions,
        top_k=args.top_k,
    )

    print(f"Query: {args.query}")
    for i, (record, score) in enumerate(results, start=1):
        print(f"{i}. id={record.id} score={score:.4f} summary={record.summary}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.embedding.cli",
        description="Local embedding pipeline for diary summaries",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Generate and save embeddings")
    index_parser.add_argument("--input", required=True, help="Path to CSV/JSON containing summary")
    index_parser.add_argument("--backend", choices=["json", "sqlite"], default="sqlite")
    index_parser.add_argument("--output", required=True, help="Output file path (.json or .db)")
    index_parser.add_argument("--dimensions", type=int, default=256)
    index_parser.set_defaults(func=cmd_index)

    search_parser = subparsers.add_parser("search", help="Run similarity search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--backend", choices=["json", "sqlite"], default="sqlite")
    search_parser.add_argument("--store", required=True, help="Embedding store path")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--dimensions", type=int, default=256)
    search_parser.set_defaults(func=cmd_search)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
