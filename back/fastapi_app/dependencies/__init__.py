from fastapi import Depends, HTTPException, status
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from starlette.requests import Request
import jwt
from django.conf import settings
from typing import Optional

async def get_current_user(request: Request) -> Optional[User]:
    authorization = request.headers.get('Authorization')
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    token = authorization.replace('Bearer ', '')
    try:
        payload = jwt.decode(
            token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithms=[settings.SIMPLE_JWT['ALGORITHM']]
        )
        user_id = payload.get('user_id')
        if user_id:
            UserModel = get_user_model()
            try:
                return await sync_to_async(UserModel.objects.get)(id=user_id)
            except UserModel.DoesNotExist:
                pass
    except jwt.PyJWTError:
        return None
    
    return None

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
