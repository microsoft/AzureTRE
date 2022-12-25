import logging
import traceback

from fastapi import Request
from fastapi.responses import PlainTextResponse

from core import config
from resources import strings


async def generic_error_handler(_: Request, exception: Exception) -> PlainTextResponse:
    logging.debug("=====================================")
    logging.exception(exception)
    logging.debug("=====================================")
    error_string = traceback.format_exc() if config.DEBUG else strings.UNABLE_TO_PROCESS_REQUEST
    return PlainTextResponse(error_string, status_code=500)
