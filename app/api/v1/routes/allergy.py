from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user, get_session

from app.models.user import User
from app.schemas.allergy import AllergyCreateRequest, AllergyResponse
from app.services.allergy_service import AllergyService

router = APIRouter(prefix="/allergy")

@router.get("/list",response_model=list[AllergyResponse])
async def list_allergies(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    allergys = AllergyService(session)
    return await allergys.get_allergies_by_user(user.id)

@router.get("/{allergy_id}",response_model=AllergyResponse)
async def get_allergy(allergy_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    allergys = AllergyService(session)
    return await allergys.get_allergy_by_id(user.id, allergy_id)

@router.post("/create",response_model=AllergyResponse)
async def create_allergy(allergy_data: AllergyCreateRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    allergys = AllergyService(session)
    return await allergys.create_allergy(user.id, allergy_data)