import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.trend_analysis.lab_trend_service import LabTrendService as AILabTrendService
from app.repositories.lab_result_repository import LabResultRepository


class LabTrendService:
    def __init__(self, session: AsyncSession) -> None:
        self.lab_repo = LabResultRepository(session)
        self.impl = AILabTrendService()

    async def trends(self, user_id: uuid.UUID) -> list[dict]:
        rows = list(await self.lab_repo.list_by_user(user_id))
        return self.impl.build_trends(rows)
