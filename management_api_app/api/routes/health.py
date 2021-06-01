from datetime import datetime
from fastapi import APIRouter
from models.schemas.health import Pong
from resources import strings


router = APIRouter()


@router.get("/health", name=strings.API_GET_HEALTH_STATUS)
async def ping_server() -> Pong:
    return Pong(message=strings.PONG, time=datetime.now())
