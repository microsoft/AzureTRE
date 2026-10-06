import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from mock import patch
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

pytestmark = pytest.mark.asyncio


@pytest.fixture
def instrumented_app():
    from main import get_application

    with patch("main.config.ENABLE_LOCAL_DEBUGGING", True):
        app = get_application()

    FastAPIInstrumentor.instrument_app(app)
    try:
        yield app
    finally:
        FastAPIInstrumentor.uninstrument_app(app)


@pytest_asyncio.fixture
async def instrumented_client(instrumented_app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=instrumented_app),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_instrumented_nested_route(instrumented_client: AsyncClient):
    response = await instrumented_client.get("/api/ping")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "pong"


async def test_instrumented_cors_preflight(instrumented_client: AsyncClient):
    response = await instrumented_client.options(
        "/api/ping",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
