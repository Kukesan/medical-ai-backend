from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RecordType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "record_types"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    json_schema: Mapped[dict] = mapped_column("schema", JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    identity_field: Mapped[str | None] = mapped_column(String(100), nullable=True)

    medical_records = relationship("MedicalRecord", back_populates="record_type")
