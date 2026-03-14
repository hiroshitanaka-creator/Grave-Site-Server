from __future__ import annotations

from fastapi import FastAPI

from src.api.router import router

app = FastAPI(
    title="Grave Site GPTs Actions API",
    version="0.1.0",
    description="ChatGPT Custom GPTs Actions から Cloud Run 経由で家族向けメッセージを保存する API。",
)

app.include_router(router)
