from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.api import deps
from app.core.config import settings
from app.core.realtime import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...)) -> None:
    # Le CORS ne protège pas les WebSocket : on vérifie l'origine nous-mêmes.
    origin = ws.headers.get("origin")
    if origin and origin not in settings.BACKEND_CORS_ORIGINS:
        await ws.close(code=1008)
        return

    # Accès DB synchrone -> threadpool, pour ne pas bloquer la boucle d'événements.
    user = await run_in_threadpool(deps.get_user_from_token, token)
    if user is None:
        await ws.close(code=1008)
        return

    await manager.connect(user.id, ws)
    try:
        while True:
            msg = await ws.receive_text()  # le client envoie "ping" régulièrement
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user.id, ws)
