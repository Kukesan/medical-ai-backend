import uuid
from datetime import date
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.trend_analysis.lab_trend_service import LabTrendService as AILabTrendService
from app.services.medical_record_service import MedicalRecordService


class LabTrendService:
    def __init__(self, session: AsyncSession) -> None:
        self.record_service = MedicalRecordService(session)
        self.impl = AILabTrendService()

    async def trends(self, user_id: uuid.UUID) -> list[dict]:
        records = await self.record_service.list_data_by_type(user_id, "LAB_RESULT")
        rows = [
            SimpleNamespace(
                test_name=record.data.get("test_name"),
                value=record.data.get("value"),
                reference_range=record.data.get("reference_range"),
                observed_date=_parse_date(record.data.get("observed_date")),
            )
            for record in records
        ]
        return self.impl.build_trends(rows)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
