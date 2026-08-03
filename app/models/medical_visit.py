import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicalVisit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "medical_visits"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_documents.id"), nullable=False, index=True
    )
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    doctor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diagnosis_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="visits")
    document = relationship("MedicalDocument", back_populates="visits")
    medications = relationship("Medication", back_populates="visit", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="visit", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="visit", cascade="all, delete-orphan")
