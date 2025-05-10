from fastapi import FastAPI
from .routers import network, materials, groups, auth

app = FastAPI(
    title="Network Topology API",
    description="",
    version="1.0.0",
    contact={
        "name": "Network API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
    }
)

app.include_router(network.router)
app.include_router(materials.router)
app.include_router(groups.router)
app.include_router(auth.router)

@app.on_event("startup")
async def startup():
    pass

@app.on_event("shutdown")
async def shutdown():
    from .routers.network import topology_manager
    topology_manager.stop_network()