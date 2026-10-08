import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import AI_LIMIT, limiter
from app.core.dependencies import get_current_user, get_session
from app.models.user import User
from app.schemas.chat import ChatAskRequest, ChatHistoryResponse, ChatMessageOut, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse)
@limiter.limit(AI_LIMIT)
async def ask_chat(
    request: Request,
    payload: ChatAskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    svc = ChatService(session)
    result = await svc.ask(
        user.id,
        payload.question,
        uuid.UUID(payload.session_id) if payload.session_id else None,
    )

    warning = result.get("warning")
    warning_obj = (
        {"message": warning, "recommend_doctor_consult": True} if warning else None
    )

    return ChatResponse(
        session_id=result["session_id"],
        answer=result["answer"],
        confidence=result["confidence"],
        citations=result.get("citations", []),
        warning=warning_obj,
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatHistoryResponse:
    svc = ChatService(session)
    rows = await svc.history(user.id, session_id)

    return ChatHistoryResponse(
        session_id=str(session_id),
        messages=[
            ChatMessageOut(
                role=r.role,
                content=r.content,
                confidence=r.confidence,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )
