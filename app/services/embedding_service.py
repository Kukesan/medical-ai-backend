import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.service import EmbeddingService as AIEmbeddingService
from app.models.embedding import Embedding
from app.models.medical_document import MedicalDocument
from app.models.medical_record import MedicalRecord
from app.models.record_type import RecordType
from app.repositories.embedding_repository import EmbeddingRepository, SourceType


class EmbeddingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmbeddingRepository(session)
        self.impl = AIEmbeddingService()

    async def embed_document(self, user_id: uuid.UUID, document: MedicalDocument) -> None:
        text = document.embedding_text or document.ocr_text
        if not text:
            return

        await self.repo.delete_by_document_id(document.id)

        chunks = self._chunk(text)
        vectors = await self.impl.embed_texts(chunks)

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            await self.repo.create(
                Embedding(
                    user_id=user_id,
                    document_id=document.id,
                    chunk_id=f"document-{document.id}-{idx}",
                    chunk_text=chunk,
                    vector_metadata={
                        "source_document_id": str(document.id),
                        "chunk_text": chunk,
                        "type": "document",
                    },
                    embedding=vector,
                )
            )

    async def embed_medical_record(
        self, user_id: uuid.UUID, record: MedicalRecord, record_type: RecordType
    ) -> None:
        text = self._record_to_text(record, record_type)
        if not text:
            return

        await self.repo.delete_by_record_id(record.id)

        vectors = await self.impl.embed_texts([text])
        if not vectors:
            return

        await self.repo.create(
            Embedding(
                user_id=user_id,
                record_id=record.id,
                chunk_id=f"record-{record.id}",
                chunk_text=text,
                vector_metadata={
                    "source_record_id": str(record.id),
                    "record_type": record_type.code,
                    "chunk_text": text,
                    "type": "medical_record",
                },
                embedding=vectors[0],
            )
        )

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        await self.repo.delete_by_document_id(document_id)

    async def delete_by_record(self, record_id: uuid.UUID) -> None:
        await self.repo.delete_by_record_id(record_id)

    async def search(
        self,
        user_id: uuid.UUID,
        question: str,
        top_k: int = 5,
        source_type: SourceType | None = None,
    ) -> list[dict]:
        vectors = await self.impl.embed_texts([question])
        if not vectors:
            return []

        hits = await self.repo.search(user_id, vectors[0], top_k=top_k, source_type=source_type)
        return [
            {"score": 1.0 - distance, "metadata": embedding.vector_metadata}
            for embedding, distance in hits
        ]

    @staticmethod
    def _chunk(text: str, size: int = 1000) -> list[str]:
        return [text[i : i + size] for i in range(0, len(text), size)]

    @staticmethod
    def _record_to_text(record: MedicalRecord, record_type: RecordType) -> str:
        fields = ", ".join(
            f"{key}: {value}" for key, value in record.data.items() if value not in (None, "")
        )
        if not fields:
            return ""
        return f"{record_type.name}: {fields}"
