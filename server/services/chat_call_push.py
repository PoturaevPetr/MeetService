"""HTTP в ChatService: простые пуши «Входящий звонок» / «Пропущенный звонок» (Novu)."""

from __future__ import annotations

import logging
import uuid

import httpx

from server.settings import settings

logger = logging.getLogger(__name__)


async def notify_chat_call_push(*, callee_id: uuid.UUID, caller_id: uuid.UUID, kind: str) -> None:
    """
    kind: incoming | missed
    """
    base = (settings.CHAT_SERVICE_INTERNAL_BASE_URL or "").strip().rstrip("/")
    secret = (settings.INTERNAL_DELIVERY_SECRET or "").strip()
    if not base or not secret:
        logger.warning(
            "Meet→Chat push skipped: set CHAT_SERVICE_INTERNAL_BASE_URL and INTERNAL_DELIVERY_SECRET "
            "(incoming/missed call pushes will not reach Novu)"
        )
        return
    if kind not in ("incoming", "missed"):
        logger.warning("Meet→Chat push: unknown kind %s", kind)
        return
    url = f"{base}/api/internal/meet-call-push"
    body = {"callee_id": str(callee_id), "caller_id": str(caller_id), "kind": kind}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.post(url, headers={"X-Internal-Secret": secret}, json=body)
        if r.status_code not in (200, 204):
            logger.warning("Meet→Chat push HTTP %s: %s", r.status_code, (r.text or "")[:400])
        else:
            logger.info(
                "Meet→Chat push OK kind=%s callee=%s caller=%s",
                kind,
                str(callee_id)[:8],
                str(caller_id)[:8],
            )
    except Exception:
        logger.exception("Meet→Chat push failed url=%s", url)
