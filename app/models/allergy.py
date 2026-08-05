import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship 

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Allergy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "allergies"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    substance: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reaction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    user = relationship("User", back_populates="allergies")
