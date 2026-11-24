import asyncio
import logging
from collections import defaultdict
from typing import Iterable, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Connexions WebSocket actives, groupées par utilisateur (plusieurs onglets possibles)."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # --- cycle de vie -------------------------------------------------
    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Mémorise la boucle asyncio principale (appelé au démarrage de l'app)."""
        self._loop = loop

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[user_id].add(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        self._connections[user_id].discard(ws)
        if not self._connections[user_id]:
            self._connections.pop(user_id, None)

    # --- envoi --------------------------------------------------------
    async def _send(self, user_ids: Iterable[int], event: dict) -> None:
        for uid in set(user_ids):
            for ws in list(self._connections.get(uid, ())):
                try:
                    await ws.send_json(event)
                except Exception:
                    self.disconnect(uid, ws)

    def notify(self, user_ids: Iterable[int], event: dict) -> None:
        """Appelable depuis du code SYNCHRONE (services exécutés dans le threadpool).

        Ne bloque pas et ne lève jamais : le temps réel ne doit pas casser l'envoi d'un mail.
        """
        if self._loop is None or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._send(list(user_ids), event), self._loop)
        except Exception:  # pragma: no cover
            logger.exception("Échec de la notification temps réel")


manager = ConnectionManager()
