import logging
from resources import strings

from fastapi import Request
from fastapi.responses import PlainTextResponse


async def generic_error_handler(_: Request, exception: Exception) -> PlainTextResponse:
    logging.debug("=====================================")
    logging.exception(exception)
    logging.debug("=====================================")
    return PlainTextResponse(strings.UNABLE_TO_PROCESS_REQUEST, status_code=500)
