import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.allergy_repository import AllergyRepository
from app.repositories.medication_repository import MedicationRepository
from app.services.drug_interaction_service import DrugInteractionService


class MedicationAnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.med_repo = MedicationRepository(session)
        self.allergy_repo = AllergyRepository(session)
        self.interactions = DrugInteractionService()

    async def analyze(self, user_id: uuid.UUID) -> dict:
        meds = list(await self.med_repo.list_by_user(user_id))
        allergies = {item.substance for item in await self.allergy_repo.list_by_user(user_id)}
        return self.interactions.analyze(meds, allergies)
