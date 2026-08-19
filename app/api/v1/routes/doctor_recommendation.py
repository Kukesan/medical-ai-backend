from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.core.exceptions import NotFoundException
from app.models.enums import AlertCategory
from app.models.user import User
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.doctor_recommendation import DoctorSearchRequest, DoctorSearchResponse
from app.services.doctor_recommendation_service import DoctorRecommendationService
from app.services.specialty_mapper import map_to_specialty

router = APIRouter(prefix="/doctor-recommendation")


@router.post("/search", response_model=DoctorSearchResponse)
async def search_doctors(
    payload: DoctorSearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DoctorSearchResponse:
    specialty = payload.specialty_override

    if not specialty:
        if payload.analysis_result_id:
            repo = AnalysisRepository(session)
            result = await repo.get_by_user_and_id(user.id, payload.analysis_result_id)
            if not result:
                raise NotFoundException("Analysis result not found")
            specialty = map_to_specialty(
                result.category,
                result.title,
                result.description,
                result.clinical_reason,
                result.recommendation,
            )
        else:
            specialty = map_to_specialty(AlertCategory.MEDICATION_CHANGE)

    doctors, message = await DoctorRecommendationService().search(specialty, payload.location)

    return DoctorSearchResponse(
        specialty=specialty,
        availability=payload.availability,
        doctors=doctors,
        message=message,
    )
