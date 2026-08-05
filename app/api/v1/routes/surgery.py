from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_session

from app.models.user import User
from app.schemas.surgery import SurgeryCreateRequest, SurgeryResponse
from app.schemas.surgery import SurgeryCreateRequest, SurgeryResponse
from app.services.surgery_service import SurgeryService

router = APIRouter(prefix="/surgery")

@router.get("/list",response_model=list[SurgeryResponse])
async def list_surgeries(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    surgeries = SurgeryService(session)
    return await surgeries.get_surgeries_by_user(user.id)

@router.get("/{surgery_id}",response_model=SurgeryResponse)
async def get_surgery(surgery_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    surgeries = SurgeryService(session)
    return await surgeries.get_surgery_by_id(user.id, surgery_id)

@router.post("/create",response_model=SurgeryResponse)
async def create_surgery(surgery_data: SurgeryCreateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    surgeries = SurgeryService(session)
    return await surgeries.create_surgery(user.id, surgery_data)

@router.delete("/{surgery_id}")
async def delete_surgery(surgery_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    surgeries = SurgeryService(session)
    return await surgeries.delete_surgery(user.id, surgery_id)