import pytest
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

pytestmark = pytest.mark.asyncio


# Regression test for pydantic v2 OpenAPI generation.
# Response model examples embedded raw Property model instances in
# json_schema_extra, which broke schema generation with
# "TypeError: unhashable type: 'Property'".
@pytest.mark.filterwarnings("ignore::UserWarning")
async def test_openapi_schema_generates(app: FastAPI):
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )

    assert schema["paths"], "OpenAPI schema should contain paths"
    assert schema["components"]["schemas"], "OpenAPI schema should contain component schemas"
