from sqlalchemy.ext.asyncio import AsyncSession
from app.models.clinical_note import ClinicalNote

class ClinicalNoteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, clinical_note: ClinicalNote):
        self.session.add(clinical_note)
        await self.session.commit()
        await self.session.refresh(clinical_note)
        return clinical_note

    
    