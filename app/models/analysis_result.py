import uuid

from sqlalchemy import Enum, Float, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import RiskLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AnalysisResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analysis_results"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    result_type: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user = relationship("User", back_populates="analysis_results")
