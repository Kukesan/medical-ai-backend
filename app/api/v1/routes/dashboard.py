from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.analysis import AlertItem
from app.schemas.lab import LabTrendsResponse
from app.schemas.timeline import TimelineListResponse
from app.services.lab_trend_service import LabTrendService
from app.services.medication_analysis_service import MedicationAnalysisService
from app.services.timeline_service import TimelineService

router = APIRouter()


@router.get("/timeline", response_model=list[TimelineListResponse])
async def timeline(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TimelineListResponse]:
    svc = TimelineService(session)
    latest = await svc.get_by_user_id(user.id)
    return latest


@router.get("/medications", response_model=list[str])
async def medications(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    svc = MedicationAnalysisService(session)
    result = await svc.analyze(user.id)
    names = {
        item["details"].split(" appears in ")[0]
        for item in result.get("duplicate_medications", [])
        if "details" in item
    }
    return sorted(names)


@router.get("/lab-trends", response_model=LabTrendsResponse)
async def lab_trends(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LabTrendsResponse:
    svc = LabTrendService(session)
    trends = await svc.trends(user.id)
    return LabTrendsResponse(
        trends=trends,
        warning={
            "message": "Trend output is informational and not diagnostic.",
            "recommend_doctor_consult": True,
        },
    )


@router.get("/alerts", response_model=list[AlertItem])
async def alerts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AlertItem]:
    svc = MedicationAnalysisService(session)
    result = await svc.analyze(user.id)

    merged = (
        result.get("duplicate_medications", [])
        + result.get("drug_interactions", [])
        + result.get("conflicting_dosages", [])
        + result.get("expired_prescriptions", [])
        + result.get("allergy_alerts", [])
    )
    return [AlertItem.model_validate(item) for item in merged]
