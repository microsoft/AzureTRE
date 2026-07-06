import asyncio
from typing import Any
import uvicorn

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import asynccontextmanager

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from starlette.exceptions import HTTPException
from starlette.middleware.errors import ServerErrorMiddleware

from api.routes.api import router as api_router
from api.errors.http_error import http_error_handler
from api.errors.validation_error import http422_error_handler
from api.errors.generic_error import generic_error_handler
from core import config
from db.events import bootstrap_database
from services.logging import initialize_logging, logger
from service_bus.deployment_status_updater import DeploymentStatusUpdater
from service_bus.airlock_request_status_update import AirlockStatusUpdater


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()
        self.is_shutting_down: bool = False

    def add(self, task: asyncio.Task[Any]) -> None:
        self._tasks.add(task)

    def discard(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)

    def get_tasks(self) -> list[asyncio.Task[Any]]:
        return list(self._tasks)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.background_tasks = BackgroundTaskManager()

    while not await bootstrap_database():
        await asyncio.sleep(5)
        logger.warning("Database connection could not be established")

    deploymentStatusUpdater = DeploymentStatusUpdater()
    await deploymentStatusUpdater.init_repos()

    airlockStatusUpdater = AirlockStatusUpdater()
    await airlockStatusUpdater.init_repos()

    def track(task: asyncio.Task[Any]) -> None:
        def _done_callback(task: asyncio.Task[Any]) -> None:
            app.state.background_tasks.discard(task)
            if app.state.background_tasks.is_shutting_down:
                return

            if task.cancelled():
                return

            try:
                exception = task.exception()
            except asyncio.CancelledError:
                return

            if exception is not None:
                logger.error(
                    f"Background task {task.get_name()} failed",
                    exc_info=(type(exception), exception, exception.__traceback__)
                )

        app.state.background_tasks.add(task)
        task.add_done_callback(_done_callback)

    track(asyncio.create_task(
        deploymentStatusUpdater.receive_messages(),
        name="deployment-status-updater"
    ))
    track(asyncio.create_task(
        airlockStatusUpdater.receive_messages(),
        name="airlock-status-updater"
    ))

    try:
        yield
    finally:
        app.state.background_tasks.is_shutting_down = True
        tasks = app.state.background_tasks.get_tasks()
        logger.info(f"Cancelling {len(tasks)} background tasks")

        for task in tasks:
            logger.debug(f"Cancelling task {task.get_name()}")
            task.cancel()

        if tasks:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=10.0
                )
                for task, result in zip(tasks, results):
                    if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                        logger.warning(
                            f"Background task {task.get_name()} raised exception during shutdown: {result}",
                            exc_info=(type(result), result, result.__traceback__)
                        )
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for background tasks to shutdown")
                pending = [t for t in tasks if not t.done()]
                for t in pending:
                    logger.warning(f"Task {t.get_name()} did not terminate in time during shutdown")


def get_application() -> FastAPI:
    application = FastAPI(
        title=config.PROJECT_NAME,
        debug=(config.LOGGING_LEVEL == "DEBUG"),
        description=config.API_DESCRIPTION,
        version=config.VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan
    )

    application.add_middleware(ServerErrorMiddleware, handler=generic_error_handler)

    # Allow local UI debugging with local API
    if config.ENABLE_LOCAL_DEBUGGING:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"])

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    application.include_router(api_router)
    return application


initialize_logging()
app = get_application()
FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
