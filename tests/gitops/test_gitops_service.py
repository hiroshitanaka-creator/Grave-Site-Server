from __future__ import annotations

import logging

import pytest

from src.gitops import ChangeProposal, FileChange, GitOpsGuardrails, GitOpsService, GuardrailViolation


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def create_branch(self, *, base_branch: str, new_branch: str, actor: str) -> None:
        self.calls.append(
            (
                "create_branch",
                {"base_branch": base_branch, "new_branch": new_branch, "actor": actor},
            )
        )

    def commit_and_push(
        self,
        *,
        branch: str,
        message: str,
        changes: tuple[FileChange, ...],
        actor: str,
    ) -> str:
        self.calls.append(
            (
                "commit_and_push",
                {
                    "branch": branch,
                    "message": message,
                    "changes": changes,
                    "actor": actor,
                },
            )
        )
        return "abc123"

    def open_pull_request(
        self,
        *,
        base_branch: str,
        branch: str,
        title: str,
        body: str,
        reviewers: tuple[str, ...],
        actor: str,
    ) -> str:
        self.calls.append(
            (
                "open_pull_request",
                {
                    "base_branch": base_branch,
                    "branch": branch,
                    "title": title,
                    "body": body,
                    "reviewers": reviewers,
                    "actor": actor,
                },
            )
        )
        return "https://example.com/pr/1"


@pytest.fixture
def proposal() -> ChangeProposal:
    return ChangeProposal(
        requester_id="user-123",
        base_branch="main",
        branch_name="feat/gitops-service",
        commit_message="feat: add gitops service",
        pr_title="feat: add gitops service",
        pr_body="Adds backend gitops orchestration",
        requested_reviewers=("reviewer1",),
        changes=(
            FileChange(path="src/gitops/service.py", content="..."),
            FileChange(path="README.md", content="..."),
        ),
    )


def test_service_uses_service_account_for_backend_calls(proposal: ChangeProposal) -> None:
    backend = FakeBackend()
    service = GitOpsService(backend=backend, service_account="svc-gitops")

    service.create_branch(proposal)
    revision = service.commit_changes(proposal)
    pr_url = service.open_pr(proposal)

    assert revision == "abc123"
    assert pr_url == "https://example.com/pr/1"
    assert [name for name, _ in backend.calls] == [
        "create_branch",
        "commit_and_push",
        "open_pull_request",
    ]
    assert all(call["actor"] == "svc-gitops" for _, call in backend.calls)


def test_guardrails_reject_disallowed_path(proposal: ChangeProposal) -> None:
    bad = ChangeProposal(
        **{
            **proposal.__dict__,
            "changes": (FileChange(path="scripts/deploy.sh", content="echo dangerous"),),
        }
    )
    guardrails = GitOpsGuardrails(allowed_targets=("src/", "README.md"))

    with pytest.raises(GuardrailViolation, match="protected path violation"):
        guardrails.validate(bad)


def test_guardrails_reject_non_conventional_commit_message(proposal: ChangeProposal) -> None:
    bad = ChangeProposal(**{**proposal.__dict__, "commit_message": "update gitops"})

    with pytest.raises(GuardrailViolation, match="commit message violation"):
        GitOpsGuardrails().validate(bad)


def test_guardrails_require_reviewers(proposal: ChangeProposal) -> None:
    bad = ChangeProposal(**{**proposal.__dict__, "requested_reviewers": ()})

    with pytest.raises(GuardrailViolation, match="at least one reviewer"):
        GitOpsGuardrails().validate(bad)


def test_audit_logs_capture_requester_and_push_context(
    proposal: ChangeProposal, caplog: pytest.LogCaptureFixture
) -> None:
    backend = FakeBackend()
    logger = logging.getLogger("tests.gitops.audit")
    service = GitOpsService(backend=backend, service_account="svc-gitops", logger=logger)

    with caplog.at_level(logging.INFO, logger="tests.gitops.audit"):
        service.commit_changes(proposal)

    assert "requester=user-123" in caplog.text
    assert "event=commit_changes" in caplog.text
    assert "svc-gitops" in caplog.text
