from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import PlainTextResponse


def http_error_handler(_: Request, exc: HTTPException) -> PlainTextResponse:
    return PlainTextResponse(exc.detail, status_code=exc.status_code)
