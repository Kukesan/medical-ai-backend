from collections.abc import Sequence
from typing import Any

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.record_type import RecordType
from app.repositories.record_type_repository import RecordTypeRepository


class RecordTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecordTypeRepository(session)

    async def get_by_code(self, code: str) -> RecordType:
        record_type = await self.repo.get_by_code(code)
        if record_type is None:
            raise NotFoundException(f"Unknown or inactive record type '{code}'")
        return record_type

    async def get_by_id(self, record_type_id) -> RecordType:
        record_type = await self.repo.get(record_type_id)
        if record_type is None:
            raise NotFoundException("Record type not found")
        return record_type

    async def list_active(self) -> Sequence[RecordType]:
        return await self.repo.list_active()

    def validate_data(self, record_type: RecordType, data: dict[str, Any]) -> None:
        validator = jsonschema.Draft202012Validator(record_type.json_schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if not errors:
            return

        messages = []
        for error in errors:
            path = ".".join(str(part) for part in error.path) or "(root)"
            messages.append(f"{path}: {error.message}")
        raise ValidationException("; ".join(messages))
