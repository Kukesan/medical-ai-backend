import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicalRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_records"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    record_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("record_types.id"), nullable=False, index=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_documents.id"), nullable=True, index=True
    )
    recorded_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(
            RecordStatus,
            name="medical_record_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=RecordStatus.NEEDS_REVIEW,
        nullable=False,
        index=True,
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    conflict_with_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=True
    )

    user = relationship("User", back_populates="medical_records")
    record_type = relationship("RecordType", back_populates="medical_records")
    source_document = relationship("MedicalDocument")
    conflict_with = relationship("MedicalRecord", remote_side="MedicalRecord.id")
    embeddings = relationship("Embedding", back_populates="record", cascade="all, delete-orphan")
