from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vaccination import Vaccination

from app.repositories.vaccination_repository import VaccinationRepository
from app.schemas.vaccination import VaccinationCreateRequest, VaccinationResponse


class VaccinationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.vaccination_repo = VaccinationRepository(session)

    async def get_vaccinations_by_user(self, user_id: str) -> list[VaccinationResponse]:
        return await self.vaccination_repo.list_by_user(user_id)

    async def get_vaccination_by_id(self, user_id: str, vaccination_id: str) -> VaccinationResponse:
        return await self.vaccination_repo.get_by_user_and_id(user_id, vaccination_id)

    async def create_vaccination(self, user_id: str, vaccination_data: VaccinationCreateRequest) -> VaccinationResponse:
        vaccination_entity = Vaccination(
            user_id=user_id,
            name=vaccination_data.name,
            date_administered=vaccination_data.date_administered,
            is_next_due=vaccination_data.is_next_due,
            next_due_date=vaccination_data.next_due_date
        )
        await self.vaccination_repo.create(vaccination_entity)
        await self.session.commit()
        return VaccinationResponse(
            id=str(vaccination_entity.id),
            user_id=str(vaccination_entity.user_id),
            name=vaccination_entity.name,
            date_administered=vaccination_entity.date_administered,
            is_next_due=vaccination_entity.is_next_due,
            next_due_date=vaccination_entity.next_due_date
        )

    async def delete_vaccination(self, user_id: str, vaccination_id: str) -> None:
        return await self.vaccination_repo.delete(user_id, vaccination_id)