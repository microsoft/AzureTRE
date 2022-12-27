from typing import Union

from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import validation_error_response_definition
from pydantic import ValidationError
from fastapi import Request, status
from fastapi.responses import PlainTextResponse


def http422_error_handler(_: Request, exception: Union[RequestValidationError, ValidationError]) -> PlainTextResponse:
    return PlainTextResponse(str(exception), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


validation_error_response_definition["properties"] = {
    "errors": {
        "title": "Errors",
        "type": "array",
        "items": {"$ref": "{0}ValidationError".format(REF_PREFIX)},
    },
}
