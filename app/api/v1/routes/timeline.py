from fastapi import APIRouter

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.timeline import TimelineListResponse
from app.services.timeline_service import TimelineService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.params import Depends
from app.core.dependencies import get_current_user, get_session

router = APIRouter(prefix="/timeline")

@router.get("/list",response_model=list[TimelineListResponse])
async def list_timeline(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    timeline_service = TimelineService(session)
    return await timeline_service.get_by_user_id(user.id)