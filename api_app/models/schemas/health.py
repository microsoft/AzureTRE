from datetime import datetime

from pydantic import BaseModel


class Pong(BaseModel):
    message: str
    time: datetime
