import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalNote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clinical_notes"

    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_visits.id"), nullable=False, index=True
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    visit = relationship("MedicalVisit", back_populates="clinical_notes")
