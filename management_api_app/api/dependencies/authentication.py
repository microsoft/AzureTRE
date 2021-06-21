from fastapi import Request

from core import config
from services.authentication import AzureADAuthorization, User


async def get_current_user_authorizer(request: Request) -> User:
    authorizer = AzureADAuthorization(config.AAD_INSTANCE, config.TENANT_ID)
    return await authorizer(request)
