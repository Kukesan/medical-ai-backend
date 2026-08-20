import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class PatientTimeline(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "patient_timeline"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_documents.id"), nullable=False, index=True
    )
    doctor_name: Mapped[str | None] = mapped_column(nullable=True)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    visit_type: Mapped[str | None] = mapped_column(nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(nullable=True)
    diagnosis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User", back_populates="timeline_entries")
    document = relationship("MedicalDocument", back_populates="timeline_entries")
