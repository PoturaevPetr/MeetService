from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.api.deps import jwt_user_id
from server.settings import settings

router = APIRouter(prefix="/config", tags=["config"])


class IceServersResponse(BaseModel):
    ice_servers: list[dict]


@router.get("/ice-servers", response_model=IceServersResponse)
async def get_ice_servers(_user_id: uuid.UUID = Depends(jwt_user_id)) -> IceServersResponse:
    return IceServersResponse(ice_servers=settings.ice_servers())
