import uuid

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import DocumentType, ProcessingStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicalDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_documents"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="document_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=DocumentType.OTHER,
        nullable=False,
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(
            ProcessingStatus,
            name="processing_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
    )
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="documents")
    visits = relationship("MedicalVisit", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
