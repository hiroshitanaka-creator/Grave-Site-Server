from __future__ import annotations

from dataclasses import dataclass
import posixpath
from pathlib import PurePosixPath
import re

from .models import ChangeProposal


class GuardrailViolation(ValueError):
    """Raised when a proposal violates protection rules."""


@dataclass(frozen=True)
class GitOpsGuardrails:
    """Protection rules for backend-enforced GitOps operations."""

    allowed_targets: tuple[str, ...] = ("src/", "README.md")
    commit_message_pattern: str = r"^(feat|fix|docs|chore|refactor|test): .+"
    require_reviewers: bool = True

    def validate(self, proposal: ChangeProposal) -> None:
        self._validate_has_changes(proposal)
        self._validate_target_directories(proposal)
        self._validate_commit_message(proposal.commit_message)
        self._validate_required_reviewers(proposal.requested_reviewers)

    def _validate_has_changes(self, proposal: ChangeProposal) -> None:
        if not proposal.changes:
            raise GuardrailViolation("change violation: at least one file change is required")

    def _validate_target_directories(self, proposal: ChangeProposal) -> None:
        for change in proposal.changes:
            if not self._is_allowed_path(change.path):
                raise GuardrailViolation(
                    f"protected path violation: '{change.path}' is outside {self.allowed_targets}"
                )

    def _is_allowed_path(self, path: str) -> bool:
        normalized = PurePosixPath(path).as_posix()
        collapsed = posixpath.normpath(normalized)

        if collapsed.startswith("/") or collapsed == ".." or collapsed.startswith("../"):
            return False

        if collapsed == ".":
            return False

        for target in self.allowed_targets:
            if target.endswith("/") and collapsed.startswith(target):
                return True
            if collapsed == target:
                return True
        return False

    def _validate_commit_message(self, message: str) -> None:
        if not re.match(self.commit_message_pattern, message):
            raise GuardrailViolation(
                "commit message violation: expected conventional style, "
                f"pattern={self.commit_message_pattern!r}"
            )

    def _validate_required_reviewers(self, requested_reviewers: tuple[str, ...]) -> None:
        if self.require_reviewers and not requested_reviewers:
            raise GuardrailViolation("review violation: at least one reviewer is required")
