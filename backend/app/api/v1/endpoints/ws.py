"""
Live alert fan-out. The pipeline orchestrator publishes CRITICAL/CAUTION
events onto a Redis pub/sub channel (see services/alert_service.py); this
websocket endpoint subscribes and relays each message to connected
dashboard clients so an officer sees alerts within ~200ms of detection
(matches test criterion T-08 in the write-up's testing table).

Auth here is via a short-lived token query param since browsers can't set
custom headers on a WebSocket handshake; the token is the same JWT issued
by /auth/login.
"""
import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security import decode_access_token

router = APIRouter()
settings = get_settings()

ALERTS_CHANNEL = "pds:alerts"


@router.websocket("/alerts")
async def alerts_ws(websocket: WebSocket, token: str = Query(...)):
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(ALERTS_CHANNEL)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is not None:
                await websocket.send_text(message["data"])
            # yield control so we can also notice client disconnects promptly
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(ALERTS_CHANNEL)
        await redis_client.close()


async def publish_alert(payload: dict) -> None:
    """Called by alert_service.py whenever a new Alert row is created."""
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.publish(ALERTS_CHANNEL, json.dumps(payload, default=str))
    finally:
        await redis_client.close()
