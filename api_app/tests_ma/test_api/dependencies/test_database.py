from mock import MagicMock
import pytest

from api.dependencies.database import Database

pytestmark = pytest.mark.asyncio


async def test_get_container_proxy():
    container_name = "test_container"
    container_proxy = await Database().get_container_proxy(container_name)
    assert isinstance(container_proxy, MagicMock)
