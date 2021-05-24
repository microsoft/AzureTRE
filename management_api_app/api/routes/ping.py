from datetime import datetime
from fastapi import APIRouter
from models.schemas.ping import Pong
from resources import strings


router = APIRouter()


@router.get("", name="ping:get-server-alive")
async def ping_server() -> Pong:
    return Pong(message=strings.PONG, time=datetime.now())
