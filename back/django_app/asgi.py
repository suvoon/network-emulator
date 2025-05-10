import os
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from django.conf import settings
from asgiref.sync import sync_to_async, AsyncToSync

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

fastapi_app = FastAPI(
    title="Network Topology API",
    description="API for managing virtual network topologies using Mininet and Scapy.",
    version="1.0.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

django_asgi_app = get_asgi_application()

from fastapi_app.routers import network, materials, groups, auth

fastapi_app.include_router(network.router)
fastapi_app.include_router(materials.router)
fastapi_app.include_router(groups.router)
fastapi_app.include_router(auth.router)

async def application(scope, receive, send):
    if scope["type"] == "http":
        path = scope["path"].rstrip('/')

        if (path.startswith("/admin") or 
            path == ""):
            await django_asgi_app(scope, receive, send)
            return
        
        if path.startswith("/api/auth"):
            await django_asgi_app(scope, receive, send)
            return
        
        if path.startswith("/api"):
            await fastapi_app(scope, receive, send)
            return
            
    await fastapi_app(scope, receive, send)

fastapi_app.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")
fastapi_app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

application = application
