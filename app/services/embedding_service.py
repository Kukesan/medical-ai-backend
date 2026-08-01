import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.service import EmbeddingService as AIEmbeddingService
from app.models.embedding import Embedding
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository


class EmbeddingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.repo = EmbeddingRepository(session)
        self.impl = AIEmbeddingService()

    async def index_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> None:
        document = await self.doc_repo.get_by_user_and_id(user_id, document_id)
        if not document or not document.ocr_text:
            return

        chunks = self._chunk(document.ocr_text)
        metadatas = [
            {
                "source_document_id": str(document.id),
                "chunk_text": chunk,
                "type": "ocr_text",
            }
            for chunk in chunks
        ]
        positions = await self.impl.add_chunks(chunks, metadatas)

        for idx, (chunk, meta) in enumerate(zip(chunks, metadatas, strict=False)):
            await self.repo.create(
                Embedding(
                    document_id=document.id,
                    chunk_id=f"{document.id}-{idx}",
                    chunk_text=chunk,
                    vector_metadata=meta,
                    vector_index_position=positions[idx],
                )
            )

        await self.session.commit()

    def _chunk(self, text: str, size: int = 1000) -> list[str]:
        return [text[i : i + size] for i in range(0, len(text), size)]

    async def search(self, question: str, top_k: int = 5) -> list[dict]:
        return await self.impl.similarity_search(question, top_k=top_k)
