import uuid
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import Embedding
from app.repositories.base import BaseRepository

SourceType = Literal["document", "medical_record"]


class EmbeddingRepository(BaseRepository[Embedding]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Embedding)

    async def list_by_document_ids(self, document_ids: list[uuid.UUID]) -> Sequence[Embedding]:
        result = await self.session.execute(select(Embedding).where(Embedding.document_id.in_(document_ids)))
        return result.scalars().all()

    async def delete_by_document_id(self, document_id: uuid.UUID) -> None:
        await self.session.execute(delete(Embedding).where(Embedding.document_id == document_id))
        await self.session.flush()

    async def delete_by_record_id(self, record_id: uuid.UUID) -> None:
        await self.session.execute(delete(Embedding).where(Embedding.record_id == record_id))
        await self.session.flush()

    async def search(
        self,
        user_id: uuid.UUID,
        query_vector: list[float],
        top_k: int = 5,
        source_type: SourceType | None = None,
    ) -> Sequence[tuple[Embedding, float]]:
        distance = Embedding.embedding.cosine_distance(query_vector)
        stmt = select(Embedding, distance).where(Embedding.user_id == user_id)
        if source_type == "document":
            stmt = stmt.where(Embedding.document_id.isnot(None))
        elif source_type == "medical_record":
            stmt = stmt.where(Embedding.record_id.isnot(None))

        stmt = stmt.order_by(distance).limit(top_k)
        result = await self.session.execute(stmt)
        return list(result.all())
