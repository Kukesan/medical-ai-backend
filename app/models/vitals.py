import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Vitals(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vitals"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    pressure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_sugar: Mapped[float | None] = mapped_column(Float, nullable=True)

    user = relationship("User", back_populates="vitals")
