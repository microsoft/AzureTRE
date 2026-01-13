import pytest

from httpx import AsyncClient, ASGITransport
from starlette.status import HTTP_404_NOT_FOUND

pytestmark = pytest.mark.asyncio


async def test_frw_validation_error_format(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/wrong_path/asd")

    assert response.status_code == HTTP_404_NOT_FOUND

    assert "Not Found" in response.text
