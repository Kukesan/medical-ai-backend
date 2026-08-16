from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.medical_record import RecordTypeResponse
from app.services.record_type_service import RecordTypeService

router = APIRouter(prefix="/record-types")


@router.get("", response_model=list[RecordTypeResponse])
async def list_record_types(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = RecordTypeService(session)
    return await service.list_active()


@router.get("/{code}", response_model=RecordTypeResponse)
async def get_record_type(
    code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = RecordTypeService(session)
    return await service.get_by_code(code)
