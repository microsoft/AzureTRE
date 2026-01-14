import pytest

from httpx import AsyncClient, ASGITransport
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT


pytestmark = pytest.mark.asyncio


async def test_frw_validation_error_format(app):
    @app.get("/wrong_path/{param}")
    def route_for_test(param: int) -> None:  # pragma: no cover
        pass

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/wrong_path/asd")

    assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT

    assert "error" in response.text
