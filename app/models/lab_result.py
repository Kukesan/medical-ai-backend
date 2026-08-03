import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LabResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "lab_results"

    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_visits.id"), nullable=False, index=True
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    visit = relationship("MedicalVisit", back_populates="lab_results")
