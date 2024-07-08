from resources import strings

from fastapi import Request
from fastapi.responses import PlainTextResponse

from services.logging import logger


async def generic_error_handler(_: Request, exception: Exception) -> PlainTextResponse:
    logger.debug("=====================================")
    logger.exception(exception)
    logger.debug("=====================================")
    return PlainTextResponse(strings.UNABLE_TO_PROCESS_REQUEST, status_code=500)
