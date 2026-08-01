from datetime import date

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
