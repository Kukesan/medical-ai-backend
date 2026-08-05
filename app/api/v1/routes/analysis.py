import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.dependencies import get_current_user
from app.database.session import SessionLocal
from app.models.user import User
from app.schemas.analysis import AnalysisRunRequest, AnalysisRunResponse
from app.services.analysis_service import AnalysisService
from app.schemas.medication_analyze import MedicationAlert

router = APIRouter(prefix="/analysis")


@router.post("/run", response_model=AnalysisRunResponse)
async def run_analysis(
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

@router.get("/results", response_model=list[MedicationAlert])
async def get_analysis_results(
    user: User = Depends(get_current_user),
 ) -> list[MedicationAlert]:
    async with SessionLocal() as session:
        service = AnalysisService(session)
        results = await service.get_analysis_results(user.id)
        return results