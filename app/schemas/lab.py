from app.schemas.base import ORMBaseSchema
from app.schemas.common import SafetyWarning


class LabTrendItem(ORMBaseSchema):
    test_name: str
    trend_direction: str
    normal_range_comparison: str
    explanation: str
    confidence: float


class LabTrendsResponse(ORMBaseSchema):
    trends: list[LabTrendItem]
    warning: SafetyWarning
