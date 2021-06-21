import logging

from fastapi import Depends, HTTPException, status

from resources import strings
from services.aad_authentication import authorize, User


async def get_current_user(user: User = Depends(authorize)) -> User:
    logging.debug(f"GETTING CURRENT USER: {str(user)}")
    return user


async def get_current_admin_user(user: User = Depends(get_current_user)) -> User:
    if 'TREAdmin' not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=strings.AUTH_NOT_ASSIGNED_TO_ADMIN_ROLE, headers={"WWW-Authenticate": "Bearer"})
    logging.debug("USER IS ADMIN")
    return user
