from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

from .models import ChangeProposal, FileChange
from .policy import GitOpsGuardrails


class GitBackend(Protocol):
    """Backend integration that runs with service-account permissions."""

    def create_branch(self, *, base_branch: str, new_branch: str, actor: str) -> None: ...

    def commit_and_push(
        self, *, branch: str, message: str, changes: tuple[FileChange, ...], actor: str
    ) -> str: ...

    def open_pull_request(
        self,
        *,
        base_branch: str,
        branch: str,
        title: str,
        body: str,
        reviewers: tuple[str, ...],
        actor: str,
    ) -> str: ...


@dataclass(frozen=True)
class GitOpsService:
    """Thin orchestration layer for validated GitOps operations."""

    backend: GitBackend
    service_account: str
    guardrails: GitOpsGuardrails = GitOpsGuardrails()
    logger: logging.Logger = logging.getLogger("gitops.audit")

    def create_branch(self, proposal: ChangeProposal) -> None:
        self.guardrails.validate(proposal)
        self.backend.create_branch(
            base_branch=proposal.base_branch,
            new_branch=proposal.branch_name,
            actor=self.service_account,
        )
        self._audit(
            event="create_branch",
            requester_id=proposal.requester_id,
            branch=proposal.branch_name,
            base_branch=proposal.base_branch,
        )

    def commit_changes(self, proposal: ChangeProposal) -> str:
        self.guardrails.validate(proposal)
        revision = self.backend.commit_and_push(
            branch=proposal.branch_name,
            message=proposal.commit_message,
            changes=proposal.changes,
            actor=self.service_account,
        )
        self._audit(
            event="commit_changes",
            requester_id=proposal.requester_id,
            branch=proposal.branch_name,
            revision=revision,
            files=[change.path for change in proposal.changes],
        )
        return revision

    def open_pr(self, proposal: ChangeProposal) -> str:
        self.guardrails.validate(proposal)
        pr_url = self.backend.open_pull_request(
            base_branch=proposal.base_branch,
            branch=proposal.branch_name,
            title=proposal.pr_title,
            body=proposal.pr_body,
            reviewers=proposal.requested_reviewers,
            actor=self.service_account,
        )
        self._audit(
            event="open_pr",
            requester_id=proposal.requester_id,
            branch=proposal.branch_name,
            reviewers=list(proposal.requested_reviewers),
            pr_url=pr_url,
        )
        return pr_url

    def _audit(self, **payload: object) -> None:
        self.logger.info(
            "gitops_audit requester=%s actor=%s event=%s details=%s",
            payload.get("requester_id"),
            self.service_account,
            payload.get("event"),
            payload,
        )
