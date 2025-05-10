from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from jose import jwt, JWTError
import os
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from pydantic import BaseModel

router = APIRouter(
    prefix="/api",
    tags=["auth"],
)

SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

class Token(BaseModel):
    access_token: str
    token_type: str
    token: str
    user: Dict[str, Any]

class TokenData(BaseModel):
    username: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = User.objects.filter(username=token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def authenticate_user(username: str, password: str):
    user = authenticate(username=username, password=password)
    return user

@router.post("/token/", response_model=Token)
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 совместимый токенный вход, получение токена для будущих запросов
    """
    user = authenticate(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": "EDUCATOR" if user.is_staff else "STUDENT",
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    } 

@router.get("/auth/users/", response_model=dict)
async def list_users(current_user: User = Depends(get_current_user)):
    """
    Вывод списка всех пользователей (для преподавателей)
    """
    is_educator = current_user.is_staff
    
    if not is_educator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only educators can view the users list",
        )
        
    users = User.objects.filter(is_staff=False)
    
    user_list = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": "STUDENT",
        }
        for user in users
    ]
    
    return {"users": user_list} 