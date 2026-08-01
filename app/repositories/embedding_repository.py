import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import Embedding
from app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository[Embedding]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Embedding)

    async def list_by_document_ids(self, document_ids: list[uuid.UUID]) -> Sequence[Embedding]:
        result = await self.session.execute(select(Embedding).where(Embedding.document_id.in_(document_ids)))
        return result.scalars().all()
