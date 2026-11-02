import re

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


@pytest.fixture
def traced_app():
    from main import get_application
    from opentelemetry.sdk.trace import TracerProvider

    app = get_application()

    async def fail():
        raise RuntimeError("synthetic failure")

    app.add_api_route("/api/test-failure", fail)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=TracerProvider())
    try:
        yield app
    finally:
        FastAPIInstrumentor.uninstrument_app(app)


@pytest.mark.parametrize("path, expected_status", [("/api/ping", 200), ("/api/test-failure", 500)])
async def test_each_response_has_the_request_id_of_its_trace(traced_app: FastAPI, path, expected_status):
    async with AsyncClient(
        transport=ASGITransport(app=traced_app, raise_app_exceptions=False), base_url="http://testserver"
    ) as client:
        first = await client.get(path)
        second = await client.get(path)

    assert first.status_code == expected_status
    assert re.fullmatch(r"\|[0-9a-f]{32}\.[0-9a-f]{16}\.", first.headers["request-id"])
    # Each request has its own trace.
    assert first.headers["request-id"][:33] != second.headers["request-id"][:33]


async def test_a_request_without_a_trace_has_no_request_id():
    from main import get_application

    async with AsyncClient(transport=ASGITransport(app=get_application()), base_url="http://testserver") as client:
        response = await client.get("/api/ping")

    assert response.status_code == status.HTTP_200_OK
    assert "request-id" not in response.headers
