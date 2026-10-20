"""Explicit Google authentication choices; credentials never enter record payloads."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def validate_auth_config() -> str:
    mode = os.getenv("GOOGLE_AUTH_MODE", "service_account")
    variable = {
        "service_account": "GOOGLE_SERVICE_ACCOUNT_JSON",
        "oauth": "GOOGLE_OAUTH_TOKEN_JSON",
    }.get(mode)
    if mode not in {"service_account", "oauth", "adc"}:
        raise ValueError("GOOGLE_AUTH_MODE must be service_account, oauth or adc")
    if variable:
        path = os.getenv(variable, "")
        if not path:
            raise ValueError(
                f"環境変数 {variable} が未設定です。認証JSONへのパスを設定してください。"
            )
        if not Path(path).is_file():
            raise ValueError(f"{variable} のファイルが見つかりません")
    return mode


def credentials_for(scopes: list[str]) -> Any:
    mode = validate_auth_config()
    try:
        if mode == "oauth":
            from google.oauth2.credentials import Credentials

            return Credentials.from_authorized_user_file(
                os.environ["GOOGLE_OAUTH_TOKEN_JSON"], scopes
            )
        if mode == "service_account":
            from google.oauth2.service_account import Credentials

            return Credentials.from_service_account_file(
                os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"],
                scopes=scopes,
            )
        import google.auth

        return google.auth.default(scopes=scopes)[0]
    except ImportError as exc:
        raise ValueError("Install grave-site-server[google] for Google API access") from exc
    except Exception as exc:
        raise ValueError(f"Google credential initialization failed ({type(exc).__name__})") from exc


def build_google_service(api: str, version: str, scopes: list[str]) -> Any:
    try:
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
        from googleapiclient.discovery import build

        return build(
            api,
            version,
            http=AuthorizedHttp(credentials_for(scopes), http=httplib2.Http(timeout=30)),
            cache_discovery=False,
        )
    except ImportError as exc:
        raise ValueError("Install grave-site-server[google] for Google API access") from exc


def http_status(exc: Exception) -> int | None:
    return getattr(getattr(exc, "resp", None), "status", None)
