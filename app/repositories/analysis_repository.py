import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult
from app.models.enums import RiskLevel
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisResult]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AnalysisResult)

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 100) -> Sequence[AnalysisResult]:
        result = await self.session.execute(
            select(AnalysisResult)
            .where(AnalysisResult.user_id == user_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_important_by_user(
        self,
        user_id: uuid.UUID,
        risk_levels: Sequence[RiskLevel] = (RiskLevel.HIGH, RiskLevel.MEDIUM),
        limit: int = 100,
    ) -> Sequence[AnalysisResult]:
        result = await self.session.execute(
            select(AnalysisResult)
            .where(AnalysisResult.user_id == user_id, AnalysisResult.risk_level.in_(risk_levels))
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_user_and_id(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> AnalysisResult | None:
        result = await self.session.execute(
            select(AnalysisResult)
            .where(AnalysisResult.user_id == user_id, AnalysisResult.id == analysis_id)
        )
        return result.scalar_one_or_none()
