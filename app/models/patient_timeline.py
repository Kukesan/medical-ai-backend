import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class PatientTimeline(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "patient_timeline"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    doctor_name: Mapped[str] = mapped_column(nullable=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    visit_type: Mapped[str] = mapped_column(nullable=True)
    hospital_name: Mapped[str] = mapped_column(nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
