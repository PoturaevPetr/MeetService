from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.auth.jwt import JwtAuthError, get_user_id_from_access_token
from server.db.session import SessionLocal
from server.schemas.signaling import Ping, parse_client_message
from server.services import call_service
from server.settings import settings
from server.ws.connection_manager import manager

router = APIRouter()


def _db() -> Any:
    return SessionLocal()


async def _notify_peer(
    call,
    from_user_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    peer = call.callee_id if from_user_id == call.caller_id else call.caller_id
    await manager.send_json(peer, payload)


@router.websocket("/ws/signaling")
async def signaling_websocket(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token (тот же, что у ChatService)"),
) -> None:
    if not token:
        await websocket.close(code=4401)
        return

    try:
        user_id = get_user_id_from_access_token(token)
    except JwtAuthError:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await manager.connect(user_id, websocket)

    await websocket.send_json({"type": "connected", "user_id": str(user_id)})
    await websocket.send_json({"type": "signal.ice_servers", "ice_servers": settings.ice_servers()})

    try:
        while True:
            text = await websocket.receive_text()
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid json"})
                continue

            if not isinstance(raw, dict):
                await websocket.send_json({"type": "error", "message": "expected object"})
                continue

            msg = parse_client_message(raw)
            if msg is None:
                await websocket.send_json({"type": "error", "message": f"unknown type: {raw.get('type')}"})
                continue

            if isinstance(msg, Ping):
                await websocket.send_json({"type": "pong"})
                continue

            db = _db()
            try:
                await _dispatch_message(db, websocket, user_id, msg)
            finally:
                db.close()

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)


async def _dispatch_message(db, websocket: WebSocket, user_id: uuid.UUID, msg: Any) -> None:
    from server.schemas.signaling import (
        CallAccept,
        CallCancel,
        CallEnd,
        CallInvite,
        CallReject,
        WebrtcIceCandidate,
        WebrtcOffer,
        WebrtcAnswer,
    )

    if isinstance(msg, CallInvite):
        try:
            row = call_service.create_call(
                db,
                caller_id=user_id,
                callee_id=msg.callee_user_id,
                room_id=msg.room_id,
            )
        except ValueError as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            return

        await manager.send_json(
            msg.callee_user_id,
            {
                "type": "call.incoming",
                "call_id": str(row.id),
                "caller_id": str(user_id),
                "room_id": str(row.room_id) if row.room_id else None,
            },
        )
        await websocket.send_json(
            {"type": "call.created", "call_id": str(row.id), "status": row.status.value},
        )
        return

    call_id = getattr(msg, "call_id", None)
    if call_id is None:
        await websocket.send_json({"type": "error", "message": "missing call_id"})
        return

    row = call_service.get_call(db, call_id)
    if row is None:
        await websocket.send_json({"type": "error", "message": "call not found"})
        return

    try:
        call_service.assert_participant(row, user_id)
    except PermissionError:
        await websocket.send_json({"type": "error", "message": "forbidden"})
        return

    if isinstance(msg, CallAccept):
        try:
            row = call_service.accept_call(db, row, user_id)
        except ValueError as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            return
        await manager.send_json(
            row.caller_id,
            {"type": "call.accepted", "call_id": str(row.id), "callee_id": str(row.callee_id)},
        )
        await websocket.send_json({"type": "call.accept", "call_id": str(row.id), "status": row.status.value})
        return

    if isinstance(msg, (CallReject, CallCancel)):
        try:
            row = call_service.reject_call(db, row, user_id)
        except (ValueError, PermissionError) as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            return
        peer = row.callee_id if user_id == row.caller_id else row.caller_id
        await manager.send_json(
            peer,
            {
                "type": "call.rejected" if msg.type == "call.reject" else "call.cancelled",
                "call_id": str(row.id),
                "by_user_id": str(user_id),
                "status": row.status.value,
            },
        )
        return

    if isinstance(msg, CallEnd):
        try:
            row = call_service.end_call(db, row, user_id)
        except (ValueError, PermissionError) as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            return
        peer = row.callee_id if user_id == row.caller_id else row.caller_id
        await manager.send_json(
            peer,
            {"type": "call.ended", "call_id": str(row.id), "by_user_id": str(user_id)},
        )
        return

    if isinstance(msg, WebrtcOffer):
        if row.status.value not in ("ringing", "active"):
            await websocket.send_json({"type": "error", "message": "invalid call status for offer"})
            return
        await _notify_peer(
            row,
            user_id,
            {"type": "webrtc.offer", "call_id": str(row.id), "sdp": msg.sdp},
        )
        return

    if isinstance(msg, WebrtcAnswer):
        if row.status.value not in ("ringing", "active"):
            await websocket.send_json({"type": "error", "message": "invalid call status for answer"})
            return
        await _notify_peer(
            row,
            user_id,
            {"type": "webrtc.answer", "call_id": str(row.id), "sdp": msg.sdp},
        )
        return

    if isinstance(msg, WebrtcIceCandidate):
        if row.status.value not in ("ringing", "active"):
            await websocket.send_json({"type": "error", "message": "invalid call status for ice"})
            return
        cand: Any = msg.candidate
        if isinstance(cand, str):
            try:
                cand = json.loads(cand)
            except json.JSONDecodeError:
                cand = {"candidate": cand}
        await _notify_peer(
            row,
            user_id,
            {"type": "webrtc.ice_candidate", "call_id": str(row.id), "candidate": cand},
        )
        return
