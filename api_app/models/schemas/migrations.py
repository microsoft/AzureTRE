from typing import List

from pydantic import BaseModel


class Migration(BaseModel):
    """
    Migration
    """
    issueNumber: str
    status: str


class MigrationOutList(BaseModel):
    migrations: List[Migration]
