from datetime import datetime

from pydantic import BaseModel
from uuid import UUID

class VaccinationCreateRequest(BaseModel):
    name: str
    date_administered: datetime
    is_next_due: bool = False
    next_due_date: datetime | None = None

class VaccinationResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    date_administered: datetime
    is_next_due: bool
    next_due_date: datetime | None = None