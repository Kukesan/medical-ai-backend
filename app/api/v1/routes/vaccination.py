from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_session

from app.models.user import User
from app.schemas.vaccination import VaccinationCreateRequest, VaccinationResponse
from app.services.vaccination_service import VaccinationService

router = APIRouter(prefix="/vaccination")

@router.get("/list",response_model=list[VaccinationResponse])
async def list_vaccinations(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    vaccinations = VaccinationService(session)
    return await vaccinations.get_vaccinations_by_user(user.id)

@router.get("/{vaccination_id}",response_model=VaccinationResponse)
async def get_vaccination(vaccination_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    vaccinations = VaccinationService(session)
    return await vaccinations.get_vaccination_by_id(user.id, vaccination_id)

@router.post("/create",response_model=VaccinationResponse)
async def create_vaccination(vaccination_data: VaccinationCreateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    vaccinations = VaccinationService(session)
    return await vaccinations.create_vaccination(user.id, vaccination_data)

@router.delete("/{vaccination_id}")
async def delete_vaccination(vaccination_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    vaccinations = VaccinationService(session)
    return await vaccinations.delete_vaccination(user.id, vaccination_id)