import logging

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from core import config
from resources import strings


async def generic_error_handler(_: Request, exception: Exception) -> PlainTextResponse:
    logging.debug("=====================================")
    logging.debug("=====================================")
    logging.exception(exception)
    logging.debug("=====================================")
    logging.debug("=====================================")
    if config.DEBUG:
        return PlainTextResponse(exception, status_code=500)
    else:
        return PlainTextResponse(strings.UNABLE_TO_PROCESS_REQUEST, status_code=500)
