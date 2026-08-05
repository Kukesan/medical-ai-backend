from pydantic import BaseModel
from uuid import UUID

class AllergyResponse(BaseModel):
    id: UUID
    substance: str
    severity: str
    reaction: str

class AllergyCreateRequest(BaseModel):
    substance: str
    severity: str
    reaction: str