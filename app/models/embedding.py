import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embeddings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_documents.id"), nullable=True, index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=True, index=True
    )
    chunk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions), nullable=False
    )

    document = relationship("MedicalDocument", back_populates="embeddings")
    record = relationship("MedicalRecord", back_populates="embeddings")
