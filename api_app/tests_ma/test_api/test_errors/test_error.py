import pytest

from httpx import AsyncClient
from starlette.status import HTTP_404_NOT_FOUND

pytestmark = pytest.mark.asyncio


async def test_frw_validation_error_format(app):
    async with AsyncClient(base_url="http://testserver", app=app) as client:
        response = await client.get("/wrong_path/asd")

    assert response.status_code == HTTP_404_NOT_FOUND

    assert "Not Found" in response.text
