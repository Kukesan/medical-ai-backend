import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IntakeStatus
from app.models.record_intake_session import RecordIntakeSession
from app.repositories.base import BaseRepository

ACTIVE_STATUSES = (IntakeStatus.AWAITING_CLARIFICATION, IntakeStatus.AWAITING_CONFIRMATION)


class RecordIntakeRepository(BaseRepository[RecordIntakeSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RecordIntakeSession)

    async def list_active_for_user(self, user_id: uuid.UUID) -> Sequence[RecordIntakeSession]:
        stmt = (
            select(RecordIntakeSession)
            .where(RecordIntakeSession.user_id == user_id, RecordIntakeSession.status.in_(ACTIVE_STATUSES))
            .order_by(RecordIntakeSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
