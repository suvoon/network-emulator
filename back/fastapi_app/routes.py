from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from starlette.middleware.cors import CORSMiddleware
from .routers import auth, network, materials
from .dependencies import get_current_active_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(network.router)
app.include_router(materials.router)

api_router = APIRouter()

@api_router.get("/")
async def root():
    return {"message": "Network Simulator API"}

@api_router.get("/protected-route")
async def protected_route(current_user = Depends(get_current_active_user)):
    return {"message": f"Hello, {current_user.username}"}

app.include_router(api_router) 