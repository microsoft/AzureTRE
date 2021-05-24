from enum import Enum
from typing import List
from pydantic import BaseModel
from resources import strings


class StatusEnum(str, Enum):
    ok = strings.OK
    not_ok = strings.NOT_OK


class ServiceStatus(BaseModel):
    service: str = ""
    status: StatusEnum = StatusEnum.ok
    message: str = ""


class HealthCheck(BaseModel):
    services: List[ServiceStatus]
