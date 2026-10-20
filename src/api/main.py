from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.router import record_error, router
from src.messages.store import RecordConflict, RecordNotFound

app = FastAPI(
    title="Grave Site GPTs Actions API",
    version="0.2.0",
    description="ChatGPT Custom GPTs Actions から Cloud Run 経由で家族向けメッセージを保存する API。",
)

app.include_router(router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    body = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {"error": "request_error", "message": str(exc.detail)}
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    fields = sorted({".".join(map(str, error["loc"])) for error in exc.errors()})
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": "Invalid fields: " + ", ".join(fields)},
    )


@app.exception_handler(RecordConflict)
@app.exception_handler(RecordNotFound)
async def message_error(_: Request, exc):
    status, body = record_error(exc)
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Processing interrupted; retry with the same request_id or record_id",
        },
    )


@app.get("/healthz", include_in_schema=False)
def health():
    """Liveness only; this does not certify external credentials or delivery."""
    return {"status": "alive", "version": app.version}
