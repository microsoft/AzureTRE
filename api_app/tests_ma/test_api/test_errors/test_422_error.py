import pytest

from httpx import AsyncClient
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


pytestmark = pytest.mark.asyncio


async def test_frw_validation_error_format(app):
    @app.get("/wrong_path/{param}")
    def route_for_test(param: int) -> None:  # pragma: no cover
        pass

    async with AsyncClient(base_url="http://testserver", app=app) as client:
        response = await client.get("/wrong_path/asd")

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY

    # Pydantic v2 error format: check for 'int_parsing' type in response
    assert "int_parsing" in response.text
