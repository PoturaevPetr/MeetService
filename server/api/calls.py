from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from server.api.deps import jwt_user_id
from server.db.session import get_db
from server.models.call import CallStatus
from server.services import call_service
from server.services.chat_call_push import notify_chat_call_push
from server.ws.connection_manager import manager

router = APIRouter(prefix="/calls", tags=["calls"])


class CreateCallRequest(BaseModel):
    peer_user_id: uuid.UUID = Field(..., description="Собеседник (callee)")
    room_id: uuid.UUID | None = Field(None, description="Опционально: комната чата")
    media: Literal["audio", "video"] = Field("audio", description="Старт: только голос или сразу с камерой")


class CallResponse(BaseModel):
    id: uuid.UUID
    caller_id: uuid.UUID
    callee_id: uuid.UUID
    status: str
    room_id: uuid.UUID | None
    media: str

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def _status_str(cls, v: CallStatus | str) -> str:
        if isinstance(v, CallStatus):
            return v.value
        return str(v)


@router.post("", response_model=CallResponse)
async def create_call(
    body: CreateCallRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(jwt_user_id),
) -> CallResponse:
    try:
        row = call_service.create_call(
            db,
            caller_id=user_id,
            callee_id=body.peer_user_id,
            room_id=body.room_id,
            media=body.media,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    await manager.send_json(
        body.peer_user_id,
        {
            "type": "call.incoming",
            "call_id": str(row.id),
            "caller_id": str(user_id),
            "room_id": str(row.room_id) if row.room_id else None,
            "media": row.media,
        },
    )
    # Клиент создаёт звонок через REST, не через WS call.invite — пуш «Входящий» только здесь.
    asyncio.create_task(
        notify_chat_call_push(
            callee_id=body.peer_user_id,
            caller_id=user_id,
            kind="incoming",
            media=row.media,
        ),
    )

    return CallResponse.model_validate(row)


@router.get("/{call_id}", response_model=CallResponse)
def get_call(
    call_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(jwt_user_id),
) -> CallResponse:
    row = call_service.get_call(db, call_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    try:
        call_service.assert_participant(row, user_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e)) from e

    return CallResponse.model_validate(row)
