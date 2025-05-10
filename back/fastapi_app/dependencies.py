from fastapi import Depends, HTTPException, status
from .routers.auth import get_current_user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 