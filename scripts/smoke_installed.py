"""Run with a fresh venv's python -I; never touches external Google/LLM services."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import src


def main():
    if "site-packages" not in str(Path(src.__file__).resolve()):
        raise RuntimeError("Smoke check must use an installed wheel, not the source tree")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        env = {
            **os.environ,
            "API_KEY": "wheel-smoke-test-only",
            "MESSAGE_STORE": "sqlite",
            "MESSAGE_DB_PATH": str(root / "state.db"),
            "DRIVE_ENABLED": "false",
            "CALENDAR_ENABLED": "false",
        }
        for key in ("PYTHONPATH", "K_SERVICE", "CLOUD_RUN_JOB"):
            env.pop(key, None)

        def command(*args):
            result = subprocess.run(
                [sys.executable, *args],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode:
                raise RuntimeError(f"Command failed: {args}: {result.stderr}")
            return result.stdout

        (root / "input.txt").write_text("今日は読書をして楽しい。\n", encoding="utf-8")
        command(
            "-m",
            "src.diary_cli",
            "--input",
            "input.txt",
            "--format",
            "json",
            "--output",
            "diary.json",
        )
        assert "今日は" in command("-m", "src.prompt_cli", "今日は良い日")
        for module in ("src.llm_batch", "src.gemini_diary_batch", "src.openai_diary_batch"):
            command("-m", module, "--help")
        for entrypoint in (
            "grave-diary",
            "grave-llm",
            "grave-gemini",
            "grave-prompt",
            "grave-embedding",
            "grave-deliver",
        ):
            subprocess.run(
                [str(Path(sys.executable).parent / entrypoint), "--help"],
                cwd=root,
                env=env,
                check=True,
                capture_output=True,
                timeout=30,
            )
        command(
            "-m",
            "src.embedding.cli",
            "index",
            "--input",
            "output/diary.json",
            "--output",
            "vectors.db",
        )
        command("-m", "src.embedding.cli", "search", "--query", "読書", "--store", "vectors.db")
        command("-m", "src.workflows.delivery_job", "--dry-run")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("API failed to start")
                try:
                    with urlopen(base + "/healthz", timeout=1) as result:
                        assert json.load(result)["status"] == "alive"
                    break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError("API startup timeout")

            def post(body, key="wheel-smoke-test-only"):
                request = Request(
                    base + "/actions/save-message",
                    json.dumps(body).encode(),
                    headers={"Content-Type": "application/json", "X-API-Key": key},
                )
                with urlopen(request, timeout=5) as result:
                    return json.load(result)

            body = {
                "recipient": "synthetic",
                "message": "synthetic",
                "date": "2026-10-20",
                "request_id": "wheel-test",
            }
            first = post(body)
            assert first["saved"] and first["delivery_status"] == "disabled"
            assert post(body)["record_id"] == first["record_id"]
            try:
                post(body, "wrong")
                raise AssertionError("Unauthenticated access was accepted")
            except HTTPError as exc:
                assert exc.code == 401
        finally:
            server.terminate()
            server.wait(timeout=10)
    print("Installed wheel: diary, templates, embedding, batch help, job and HTTP API passed")


if __name__ == "__main__":
    main()
