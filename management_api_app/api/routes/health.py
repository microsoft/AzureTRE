from datetime import datetime
from fastapi import APIRouter
from models.schemas.health import Pong
from resources import strings


router = APIRouter()


@router.get("/health", name="health:get-server-alive")
async def ping_server() -> Pong:
    return Pong(message=strings.PONG, time=datetime.now())
