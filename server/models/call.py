from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from server.db.base import Base


class CallStatus(str, enum.Enum):
    pending = "pending"
    ringing = "ringing"
    active = "active"
    ended = "ended"
    rejected = "rejected"
    missed = "missed"
    cancelled = "cancelled"


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    caller_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    callee_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)

    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, native_enum=False, length=32),
        nullable=False,
        default=CallStatus.ringing,
    )

    # Опциональная связь с комнатой чата (тот же UUID что в ChatService)
    room_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
