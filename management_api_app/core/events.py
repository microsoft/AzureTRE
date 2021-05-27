from typing import Callable

from fastapi import FastAPI

from db.events import connect_to_db, bootstrap_database


def create_start_app_handler(app: FastAPI) -> Callable:
    async def start_app() -> None:
        app.state.cosmos_client = None
        await connect_to_db(app)
        await bootstrap_database(app)

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:
    async def stop_app() -> None:
        pass

    return stop_app
