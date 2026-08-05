from sqlalchemy import UUID, Boolean, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

class Vaccination(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vaccinations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_administered: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_next_due: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="vaccinations")