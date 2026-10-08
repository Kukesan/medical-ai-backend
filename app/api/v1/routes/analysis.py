import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.core.rate_limiter import AI_LIMIT, limiter
from app.core.dependencies import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResponse
from app.services.analysis_service import AnalysisService
from app.schemas.medication_analyze import MedicalAnalysisListResponse, MedicalAnalysisReponse, MedicationAlert

router = APIRouter(prefix="/analysis")


@router.post("/run", response_model=AnalysisRunResponse)
@limiter.limit(AI_LIMIT)
async def run_analysis(
    request: Request,
    payload: AnalysisRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> AnalysisRunResponse:
    ids = [uuid.UUID(item) for item in payload.document_ids]

    async def _runner() -> None:
        async with SessionLocal() as session:
            service = AnalysisService(session)
            await service.run_for_documents(user.id, ids)

    background_tasks.add_task(asyncio.create_task, _runner())
    return AnalysisRunResponse(status="accepted", message="Analysis started")

@router.get("/results", response_model=list[MedicalAnalysisListResponse])
async def get_analysis_results(
    user: User = Depends(get_current_user),
 ) -> list[MedicalAnalysisListResponse]:
    async with SessionLocal() as session:
        service = AnalysisService(session)
        results = await service.get_analysis_results(user.id)
        return results

@router.get("/results/{result_id}", response_model=MedicalAnalysisReponse | None)
async def get_analysis_result_by_id(
    result_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> MedicalAnalysisReponse | None:
    async with SessionLocal() as session:
        service = AnalysisService(session)
        result = await service.get_analysis_result_by_id(user.id, result_id)
        return result

@router.post("/analyze-medication-interactions", response_model=dict)
@limiter.limit(AI_LIMIT)
async def analyze_medication_interactions(
    request: Request,
    user: User = Depends(get_current_user),
) -> dict:
    async with SessionLocal() as session:
        service = AnalysisService(session)
        result = await service.analyze_medication_interactions(user.id)
        return result