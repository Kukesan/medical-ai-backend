from datetime import date, datetime

from typing import Optional

from app.schemas.base import ORMBaseSchema


class TimelineEntry(ORMBaseSchema):
    visit_id: str
    visit_date: date | None
    doctor_name: str | None
    hospital_name: str | None
    medications: list[str]
    labs: list[str]
    notes: list[str]


class TimelineResponse(ORMBaseSchema):
    timeline: list[TimelineEntry]

class TimelineListResponse(ORMBaseSchema):
    name: Optional[str] = None
    date: Optional[datetime] | None
    category: Optional[str] = None
