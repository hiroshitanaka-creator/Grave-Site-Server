from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess

from .models import FileChange


class GitBackendError(RuntimeError):
    """Raised when backend command execution fails."""


@dataclass(frozen=True)
class GitCliBackend:
    """GitHub/Git CLI backend for GitOpsService integration."""

    repo_path: str
    remote_name: str = "origin"

    def create_branch(self, *, base_branch: str, new_branch: str, actor: str) -> None:
        del actor  # actor is tracked by audit logs in the service layer.
        self._run("git", "fetch", self.remote_name, base_branch)
        self._run("git", "checkout", "-B", new_branch, f"{self.remote_name}/{base_branch}")

    def commit_and_push(
        self, *, branch: str, message: str, changes: tuple[FileChange, ...], actor: str
    ) -> str:
        del actor
        for change in changes:
            self._write_file(change.path, change.content)
            self._run("git", "add", "--", change.path)

        self._run("git", "commit", "-m", message)
        self._run("git", "push", self.remote_name, branch)
        return self._run("git", "rev-parse", "HEAD")

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
        del actor
        args: list[str] = [
            "gh",
            "pr",
            "create",
            "--base",
            base_branch,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]
        if reviewers:
            args.extend(["--reviewer", ",".join(reviewers)])

        return self._run(*args)

    def _write_file(self, relative_path: str, content: str) -> None:
        path = os.path.join(self.repo_path, relative_path)
        parent = os.path.dirname(path)
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _run(self, *args: str) -> str:
        completed = subprocess.run(
            list(args),
            cwd=self.repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise GitBackendError(
                f"command failed: {' '.join(args)}\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        return completed.stdout.strip()
