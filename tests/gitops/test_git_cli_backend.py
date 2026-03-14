from __future__ import annotations

import subprocess
from pathlib import Path

from src.gitops.backends import GitBackendError, GitCliBackend
from src.gitops.models import FileChange


def _run(cmd: list[str], cwd: Path) -> str:
    completed = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def test_create_branch_from_remote_main(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"

    _run(["git", "init", "--bare", str(remote)], cwd=tmp_path)
    _run(["git", "clone", str(remote), str(work)], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=work)
    _run(["git", "config", "user.name", "Test User"], cwd=work)
    (work / "README.md").write_text("base\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=work)
    _run(["git", "commit", "-m", "chore: init"], cwd=work)
    _run(["git", "branch", "-M", "main"], cwd=work)
    _run(["git", "push", "-u", "origin", "main"], cwd=work)

    backend = GitCliBackend(repo_path=str(work))
    backend.create_branch(base_branch="main", new_branch="feat/test", actor="svc")

    head = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=work)
    assert head == "feat/test"


def test_commit_and_push_writes_changes_and_returns_revision(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"

    _run(["git", "init", "--bare", str(remote)], cwd=tmp_path)
    _run(["git", "clone", str(remote), str(work)], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=work)
    _run(["git", "config", "user.name", "Test User"], cwd=work)
    (work / "README.md").write_text("base\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=work)
    _run(["git", "commit", "-m", "chore: init"], cwd=work)
    _run(["git", "branch", "-M", "main"], cwd=work)
    _run(["git", "push", "-u", "origin", "main"], cwd=work)

    backend = GitCliBackend(repo_path=str(work))
    backend.create_branch(base_branch="main", new_branch="feat/write", actor="svc")

    revision = backend.commit_and_push(
        branch="feat/write",
        message="feat: add generated file",
        changes=(FileChange(path="src/generated.txt", content="hello\n"),),
        actor="svc",
    )

    assert len(revision) == 40
    assert (work / "src/generated.txt").read_text(encoding="utf-8") == "hello\n"

    pushed_revision = _run(["git", "rev-parse", "origin/feat/write"], cwd=work)
    assert pushed_revision == revision


def test_commit_and_push_checks_out_target_branch_before_commit(
    tmp_path: Path,
) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"

    _run(["git", "init", "--bare", str(remote)], cwd=tmp_path)
    _run(["git", "clone", str(remote), str(work)], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=work)
    _run(["git", "config", "user.name", "Test User"], cwd=work)
    (work / "README.md").write_text("base\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=work)
    _run(["git", "commit", "-m", "chore: init"], cwd=work)
    _run(["git", "branch", "-M", "main"], cwd=work)
    _run(["git", "push", "-u", "origin", "main"], cwd=work)

    backend = GitCliBackend(repo_path=str(work))
    backend.create_branch(base_branch="main", new_branch="feat/write", actor="svc")
    _run(["git", "checkout", "main"], cwd=work)

    revision = backend.commit_and_push(
        branch="feat/write",
        message="feat: add generated file from main checkout",
        changes=(FileChange(path="src/generated.txt", content="hello from feat\n"),),
        actor="svc",
    )

    head = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=work)
    assert head == "feat/write"
    assert _run(["git", "rev-parse", "origin/feat/write"], cwd=work) == revision


def test_open_pull_request_builds_expected_gh_command(tmp_path: Path, monkeypatch) -> None:
    backend = GitCliBackend(repo_path=str(tmp_path))
    captured: list[tuple[str, ...]] = []

    def fake_run(self: GitCliBackend, *args: str) -> str:
        captured.append(args)
        return "https://example.com/pr/12"

    monkeypatch.setattr(GitCliBackend, "_run", fake_run)

    pr_url = backend.open_pull_request(
        base_branch="main",
        branch="feat/write",
        title="feat: write",
        body="body",
        reviewers=("alice", "bob"),
        actor="svc",
    )

    assert pr_url == "https://example.com/pr/12"
    assert captured == [
        (
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            "feat/write",
            "--title",
            "feat: write",
            "--body",
            "body",
            "--reviewer",
            "alice,bob",
        )
    ]


def test_backend_error_includes_command_output(tmp_path: Path) -> None:
    backend = GitCliBackend(repo_path=str(tmp_path))

    try:
        backend._run("git", "status")
    except GitBackendError as exc:
        assert "command failed: git status" in str(exc)
    else:
        raise AssertionError("expected GitBackendError")
