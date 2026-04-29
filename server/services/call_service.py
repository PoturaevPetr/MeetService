from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from server.models.call import Call, CallStatus


def create_call(
    db: Session,
    *,
    caller_id: uuid.UUID,
    callee_id: uuid.UUID,
    room_id: uuid.UUID | None = None,
) -> Call:
    if caller_id == callee_id:
        raise ValueError("caller and callee must differ")

    row = Call(
        caller_id=caller_id,
        callee_id=callee_id,
        status=CallStatus.ringing,
        room_id=room_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_call(db: Session, call_id: uuid.UUID) -> Call | None:
    return db.get(Call, call_id)


def assert_participant(call: Call, user_id: uuid.UUID) -> None:
    if user_id not in (call.caller_id, call.callee_id):
        raise PermissionError("Not a participant of this call")


def accept_call(db: Session, call: Call, user_id: uuid.UUID) -> Call:
    assert_participant(call, user_id)
    if user_id != call.callee_id:
        raise ValueError("Only callee can accept")

    if call.status not in (CallStatus.ringing, CallStatus.pending):
        raise ValueError(f"Call cannot be accepted in status {call.status}")

    call.status = CallStatus.active
    call.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(call)
    return call


def reject_call(db: Session, call: Call, user_id: uuid.UUID) -> Call:
    assert_participant(call, user_id)
    if call.status in (CallStatus.ended, CallStatus.rejected, CallStatus.cancelled):
        return call

    if user_id == call.callee_id:
        call.status = CallStatus.rejected
    else:
        call.status = CallStatus.cancelled

    call.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(call)
    return call


def end_call(db: Session, call: Call, user_id: uuid.UUID) -> Call:
    assert_participant(call, user_id)
    if call.status in (CallStatus.ended, CallStatus.rejected, CallStatus.cancelled):
        return call

    call.status = CallStatus.ended
    call.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(call)
    return call
