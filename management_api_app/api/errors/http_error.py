from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse


def http_error_handler(_: Request, exc: HTTPException) -> PlainTextResponse:
    return PlainTextResponse(exc.detail, status_code=exc.status_code)
