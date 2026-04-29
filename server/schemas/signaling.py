"""Сообщения WebRTC-сигналинга (расширяемы под видео)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class WsEnvelope(BaseModel):
    type: str
    call_id: uuid.UUID | None = None


class CallInvite(BaseModel):
    type: Literal["call.invite"] = "call.invite"
    callee_user_id: uuid.UUID
    room_id: uuid.UUID | None = None


class CallAccept(BaseModel):
    type: Literal["call.accept"] = "call.accept"
    call_id: uuid.UUID


class CallReject(BaseModel):
    type: Literal["call.reject"] = "call.reject"
    call_id: uuid.UUID


class CallEnd(BaseModel):
    type: Literal["call.end"] = "call.end"
    call_id: uuid.UUID


class CallCancel(BaseModel):
    type: Literal["call.cancel"] = "call.cancel"
    call_id: uuid.UUID


class WebrtcOffer(BaseModel):
    type: Literal["webrtc.offer"] = "webrtc.offer"
    call_id: uuid.UUID
    sdp: str


class WebrtcAnswer(BaseModel):
    type: Literal["webrtc.answer"] = "webrtc.answer"
    call_id: uuid.UUID
    sdp: str


class WebrtcIceCandidate(BaseModel):
    type: Literal["webrtc.ice_candidate"] = "webrtc.ice_candidate"
    call_id: uuid.UUID
    candidate: dict[str, Any] | str = Field(
        ...,
        description="RTCIceCandidateInit или строка JSON от клиента",
    )


class Ping(BaseModel):
    type: Literal["ping"] = "ping"


def parse_client_message(raw: dict[str, Any]) -> BaseModel | None:
    t = raw.get("type")
    if t == "ping":
        return Ping()
    if t == "call.invite":
        return CallInvite.model_validate(raw)
    if t == "call.accept":
        return CallAccept.model_validate(raw)
    if t == "call.reject":
        return CallReject.model_validate(raw)
    if t == "call.end":
        return CallEnd.model_validate(raw)
    if t == "call.cancel":
        return CallCancel.model_validate(raw)
    if t == "webrtc.offer":
        return WebrtcOffer.model_validate(raw)
    if t == "webrtc.answer":
        return WebrtcAnswer.model_validate(raw)
    if t == "webrtc.ice_candidate":
        return WebrtcIceCandidate.model_validate(raw)
    return None
