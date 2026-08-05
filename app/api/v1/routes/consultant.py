import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.consultant import (
    ConsultantAskRequest,
    ConsultantHistoryResponse,
    ConsultantMessageOut,
    ConsultantResponse,
)
from app.services.consultant_service import ConsultantService

router = APIRouter(prefix="/consultant")


@router.post("", response_model=ConsultantResponse)
async def ask_consultant(
    payload: ConsultantAskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConsultantResponse:
    svc = ConsultantService(session)
    result = await svc.ask(
        user.id,
        payload.question,
        uuid.UUID(payload.session_id) if payload.session_id else None,
    )

    warning = result.get("warning")
    warning_obj = {"message": warning, "recommend_doctor_consult": True} if warning else None

    return ConsultantResponse(
        session_id=result["session_id"],
        answer=result["answer"],
        confidence=result["confidence"],
        citations=result.get("citations", []),
        warning=warning_obj,
    )


@router.get("/history", response_model=ConsultantHistoryResponse)
async def consultant_history(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ConsultantHistoryResponse:
    svc = ConsultantService(session)
    rows = await svc.history(user.id, session_id)

    return ConsultantHistoryResponse(
        session_id=str(session_id),
        messages=[
            ConsultantMessageOut(
                role=r.role,
                content=r.content,
                confidence=r.confidence,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )
