from sqlalchemy.ext.asyncio import AsyncSession
from app.models import allergy
from app.models import allergy
from app.models.allergy import Allergy

from app.repositories.allergy_repository import AllergyRepository
from app.schemas.allergy import AllergyCreateRequest, AllergyResponse


class AllergyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.allergy_repo = AllergyRepository(session)

    async def get_allergies_by_user(self, user_id: str) -> list[AllergyResponse]:
        return await self.allergy_repo.list_by_user(user_id)

    async def get_allergy_by_id(self, user_id: str, allergy_id: str) -> AllergyResponse:
        return await self.allergy_repo.get_by_user_and_id(user_id, allergy_id)

    async def create_allergy(self, user_id: str, allergy_data: AllergyCreateRequest) -> AllergyResponse:
        allergy_entity = Allergy(
            user_id=user_id,
            substance=allergy_data.substance,
            reaction=allergy_data.reaction,
            severity=allergy_data.severity,
            confidence=1.0  # Assuming a default confidence value; adjust as needed
        )
        await self.allergy_repo.create(allergy_entity)
        await self.session.commit()
        return AllergyResponse(
            id=str(allergy_entity.id),
            substance=allergy_entity.substance,
            reaction=allergy_entity.reaction,
            severity=allergy_entity.severity,
            confidence=allergy_entity.confidence
        )

    async def delete_allergy(self, allergy_id: str) -> None:
        allergy = await self.allergy_repo.get(allergy_id)
        if allergy is None:
            raise ValueError(f"Allergy with ID {allergy_id} not found.")
        await self.allergy_repo.delete(allergy)
        await self.session.commit()