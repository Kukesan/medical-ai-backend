import uuid

from fastapi import APIRouter, Query, Response, status
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.vitals import VitalsCreateRequest, VitalsResponse, VitalsUpdateRequest
from app.services.vitals_service import VitalsService

router = APIRouter(prefix="/vitals")


@router.get("", response_model=list[VitalsResponse])
async def list_vitals(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = VitalsService(session)
    return await service.list(user.id, limit=limit, offset=offset)


@router.post("", response_model=VitalsResponse, status_code=status.HTTP_201_CREATED)
async def create_vitals(
    payload: VitalsCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = VitalsService(session)
    return await service.create(user.id, payload)


@router.get("/{vitals_id}", response_model=VitalsResponse)
async def get_vitals(
    vitals_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = VitalsService(session)
    return await service.get(user.id, vitals_id)


@router.patch("/{vitals_id}", response_model=VitalsResponse)
async def update_vitals(
    vitals_id: uuid.UUID,
    payload: VitalsUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = VitalsService(session)
    return await service.update(user.id, vitals_id, payload)


@router.delete("/{vitals_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vitals(
    vitals_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = VitalsService(session)
    await service.delete(user.id, vitals_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
