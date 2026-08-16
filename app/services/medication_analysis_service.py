import uuid
from datetime import date
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.drug_interaction_service import DrugInteractionService
from app.services.medical_record_service import MedicalRecordService


class MedicationAnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.record_service = MedicalRecordService(session)
        self.interactions = DrugInteractionService()

    async def analyze(self, user_id: uuid.UUID) -> dict:
        medication_records = await self.record_service.list_data_by_type(user_id, "MEDICATION")
        allergy_records = await self.record_service.list_data_by_type(user_id, "ALLERGY")

        meds = [
            SimpleNamespace(
                name=record.data.get("name"),
                dosage=record.data.get("dosage"),
                frequency=record.data.get("frequency"),
                end_date=_parse_date(record.data.get("end_date")),
                visit=SimpleNamespace(document_id=record.source_document_id),
            )
            for record in medication_records
        ]
        allergies = {record.data.get("substance") for record in allergy_records if record.data.get("substance")}

        return self.interactions.analyze(meds, allergies)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
