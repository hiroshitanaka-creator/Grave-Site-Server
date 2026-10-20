"""Compatibility entry point for the shared LLM pipeline."""
try:
    from src.llm_batch import *  # noqa: F403
    from src.llm_batch import main
except ModuleNotFoundError:
    from llm_batch import *  # noqa: F403
    from llm_batch import main

if __name__ == "__main__":
    raise SystemExit(main())
