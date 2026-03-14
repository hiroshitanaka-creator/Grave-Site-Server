from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileChange:
    """A single file update proposed by the LLM."""

    path: str
    content: str


@dataclass(frozen=True)
class ChangeProposal:
    """Data-only proposal from the LLM; no direct push permissions."""

    requester_id: str
    base_branch: str
    branch_name: str
    commit_message: str
    pr_title: str
    pr_body: str
    requested_reviewers: tuple[str, ...]
    changes: tuple[FileChange, ...]
