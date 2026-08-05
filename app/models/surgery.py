from sqlalchemy import UUID, Boolean, ForeignKey, String, DateTime, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from typing import Optional

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

class Surgery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "surgeries"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="surgeries")