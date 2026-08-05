from datetime import datetime

from pydantic import BaseModel
from uuid import UUID

class SurgeryResponse(BaseModel):
    id: UUID
    name: str
    date: datetime
    notes: str

class SurgeryCreateRequest(BaseModel):
    name: str
    date: datetime
    notes: str | None = None