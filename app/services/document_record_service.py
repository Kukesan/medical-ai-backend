import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_document import MedicalDocument
from app.repositories.document_repository import DocumentRepository


@dataclass(frozen=True)
class DocumentRecord:
    """A medical record read directly off a document's classified extraction output.

    Shaped to duck-type alongside MedicalRecord (`.data`, `.source_document_id`) so
    downstream consumers can merge manually-entered and document-derived records.
    """

    document_id: uuid.UUID
    record_type_code: str
    data: dict
    recorded_at: date | None

    @property
    def source_document_id(self) -> uuid.UUID:
        return self.document_id


class DocumentRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentRepository(session)

    async def list_records(
        self,
        user_id: uuid.UUID,
        record_type_code: str | None = None,
        document_id: uuid.UUID | None = None,
    ) -> list[DocumentRecord]:
        documents = await self._resolve_documents(user_id, document_id)

        records: list[DocumentRecord] = []
        for doc in documents:
            for entry in doc.classified_records or []:
                code = entry.get("record_type_code")
                if not code or (record_type_code is not None and code != record_type_code):
                    continue
                records.append(
                    DocumentRecord(
                        document_id=doc.id,
                        record_type_code=code,
                        data=entry.get("data") or {},
                        recorded_at=self._parse_date(entry.get("recorded_at")),
                    )
                )
        return records

    async def _resolve_documents(
        self, user_id: uuid.UUID, document_id: uuid.UUID | None
    ) -> Sequence[MedicalDocument]:
        if document_id is not None:
            doc = await self.repo.get_by_user_and_id(user_id, document_id)
            return [doc] if doc else []
        return await self.repo.list_by_user(user_id)

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
