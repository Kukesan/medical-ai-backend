import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import IntakeStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RecordIntakeSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "record_intake_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[IntakeStatus] = mapped_column(
        Enum(
            IntakeStatus,
            name="record_intake_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=IntakeStatus.AWAITING_CLARIFICATION,
        nullable=False,
        index=True,
    )

    record_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("record_types.id"), nullable=True, index=True
    )
    is_new_record_type: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    draft_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    answers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    pending_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pending_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recorded_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    resulting_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=True
    )

    user = relationship("User", back_populates="record_intake_sessions")
    record_type = relationship("RecordType")
    resulting_record = relationship("MedicalRecord")
