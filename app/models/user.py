from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    pressure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_sugar: Mapped[float | None] = mapped_column(Float, nullable=True)

    documents = relationship("MedicalDocument", back_populates="user", cascade="all, delete-orphan")
    timeline_entries = relationship("PatientTimeline", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="user", cascade="all, delete-orphan")
    medical_records = relationship("MedicalRecord", back_populates="user", cascade="all, delete-orphan")
    record_intake_sessions = relationship("RecordIntakeSession", back_populates="user", cascade="all, delete-orphan")
