from sqlalchemy.ext.asyncio import AsyncSession
from app.models.surgery import Surgery

from app.repositories.surgery_repository import SurgeryRepository
from app.schemas.surgery import SurgeryCreateRequest, SurgeryResponse


class SurgeryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.surgery_repo = SurgeryRepository(session)

    async def get_surgeries_by_user(self, user_id: str) -> list[SurgeryResponse]:
        return await self.surgery_repo.list_by_user(user_id)

    async def get_surgery_by_id(self, user_id: str, surgery_id: str) -> SurgeryResponse:
        return await self.surgery_repo.get_by_user_and_id(user_id, surgery_id)

    async def create_surgery(self, user_id: str, surgery_data: SurgeryCreateRequest) -> SurgeryResponse:
        surgery_entity = Surgery(
            user_id=user_id,
            name=surgery_data.name,
            date=surgery_data.date,
            notes=surgery_data.notes
        )
        await self.surgery_repo.create(surgery_entity)
        await self.session.commit()
        return SurgeryResponse(
            id=str(surgery_entity.id),
            name=surgery_entity.name,
            date=surgery_entity.date,
            notes=surgery_entity.notes
        )

    async def delete_surgery(self, user_id: str, surgery_id: str) -> None:
        return await self.surgery_repo.delete(user_id, surgery_id)