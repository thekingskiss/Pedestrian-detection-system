from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    auth,
    cameras,
    dashboard,
    detections,
    models,
    users,
    ws,
    zones,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(zones.router, prefix="/zones", tags=["zones"])
api_router.include_router(detections.router, prefix="/detections", tags=["detections"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(alerts.rules_router, prefix="/alert-rules", tags=["alert-rules"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
