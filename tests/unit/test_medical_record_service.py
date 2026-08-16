import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.enums import RecordStatus
from app.models.medical_record import MedicalRecord
from app.models.record_type import RecordType
from app.services.medical_record_service import MedicalRecordService


class FakeRecordTypeRepository:
    def __init__(self, record_types: list[RecordType]) -> None:
        self.by_code = {rt.code: rt for rt in record_types}
        self.by_id = {rt.id: rt for rt in record_types}

    async def get_by_code(self, code: str) -> RecordType | None:
        return self.by_code.get(code.upper())

    async def get(self, record_type_id) -> RecordType | None:
        return self.by_id.get(record_type_id)

    async def list_active(self) -> list[RecordType]:
        return [rt for rt in self.by_code.values() if rt.is_active]


class FakeMedicalRecordRepository:
    def __init__(self) -> None:
        self.records: dict[uuid.UUID, MedicalRecord] = {}

    async def create(self, record: MedicalRecord) -> MedicalRecord:
        if record.id is None:
            record.id = uuid.uuid4()
        self.records[record.id] = record
        return record

    async def get(self, record_id) -> MedicalRecord | None:
        return self.records.get(record_id)

    async def list_by_user(
        self, user_id, status=None, record_type_id=None, document_id=None, limit=100, offset=0
    ) -> list[MedicalRecord]:
        items = [r for r in self.records.values() if r.user_id == user_id]
        if status is not None:
            items = [r for r in items if r.status == status]
        if record_type_id is not None:
            items = [r for r in items if r.record_type_id == record_type_id]
        if document_id is not None:
            items = [r for r in items if r.source_document_id == document_id]
        return items[offset : offset + limit]

    async def find_sole_verified(self, user_id, record_type_id) -> MedicalRecord | None:
        matches = [
            r
            for r in self.records.values()
            if r.user_id == user_id and r.record_type_id == record_type_id and r.status == RecordStatus.VERIFIED
        ]
        if len(matches) != 1:
            return None
        return matches[0]


def _allergy_type() -> RecordType:
    return RecordType(
        id=uuid.uuid4(),
        code="ALLERGY",
        name="Allergy",
        json_schema={
            "type": "object",
            "required": ["substance"],
            "additionalProperties": False,
            "properties": {
                "substance": {"type": "string"},
                "reaction": {"type": ["string", "null"]},
                "severity": {"type": ["string", "null"]},
            },
        },
        is_active=True,
        identity_field="substance",
    )


def _service(record_types: list[RecordType]) -> MedicalRecordService:
    service = MedicalRecordService(AsyncMock())
    service.repo = FakeMedicalRecordRepository()
    service.record_type_service.repo = FakeRecordTypeRepository(record_types)
    return service


@pytest.mark.asyncio
async def test_create_from_extraction_sets_needs_review() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id,
        record_type_code="ALLERGY",
        data={"substance": "Paracetamol", "reaction": "Rash"},
    )

    assert record.status == RecordStatus.NEEDS_REVIEW
    assert record.current_version == 1


@pytest.mark.asyncio
async def test_create_from_extraction_conflicts_with_differing_verified_record() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    verified = MedicalRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        record_type_id=allergy_type.id,
        status=RecordStatus.VERIFIED,
        data={"substance": "Penicillin"},
        current_version=1,
    )
    await service.repo.create(verified)

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Paracetamol"}
    )

    assert record.status == RecordStatus.CONFLICT_REQUIRES_REVIEW
    assert record.conflict_with_record_id == verified.id


@pytest.mark.asyncio
async def test_create_from_extraction_matching_identity_field_is_not_a_conflict() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    verified = MedicalRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        record_type_id=allergy_type.id,
        status=RecordStatus.VERIFIED,
        data={"substance": "penicillin"},
        current_version=1,
    )
    await service.repo.create(verified)

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )

    assert record.status == RecordStatus.NEEDS_REVIEW
    assert record.conflict_with_record_id is None


@pytest.mark.asyncio
async def test_patch_no_op_when_unchanged() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )

    updated = await service.patch(user_id, record.id, {"substance": "Penicillin"})

    assert updated.current_version == 1
    assert updated.status == RecordStatus.NEEDS_REVIEW


@pytest.mark.asyncio
async def test_patch_bumps_version_on_change() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id,
        record_type_code="ALLERGY",
        data={"substance": "Paracetamol", "reaction": "Rash"},
    )

    updated = await service.patch(user_id, record.id, {"substance": "Penicillin"})

    assert updated.current_version == 2
    assert updated.status == RecordStatus.USER_EDITED
    assert updated.data["substance"] == "Penicillin"
    assert updated.data["reaction"] == "Rash"


@pytest.mark.asyncio
async def test_patch_with_invalid_merged_data_raises_and_does_not_mutate() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )

    with pytest.raises(ValidationException):
        await service.patch(user_id, record.id, {"unexpected_field": "x"})

    assert record.current_version == 1
    assert "unexpected_field" not in record.data


@pytest.mark.asyncio
async def test_patch_on_rejected_record_raises_conflict() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )
    await service.reject(user_id, record.id)

    with pytest.raises(ConflictException):
        await service.patch(user_id, record.id, {"substance": "Amoxicillin"})


@pytest.mark.asyncio
async def test_verify_succeeds_from_needs_review() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )

    verified = await service.verify(user_id, record.id)

    assert verified.status == RecordStatus.VERIFIED


@pytest.mark.asyncio
async def test_verify_already_verified_raises_conflict() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )
    await service.verify(user_id, record.id)

    with pytest.raises(ConflictException):
        await service.verify(user_id, record.id)


@pytest.mark.asyncio
async def test_verify_from_conflict_state_raises_conflict() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    verified = MedicalRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        record_type_id=allergy_type.id,
        status=RecordStatus.VERIFIED,
        data={"substance": "Penicillin"},
        current_version=1,
    )
    await service.repo.create(verified)
    conflicting = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Paracetamol"}
    )
    assert conflicting.status == RecordStatus.CONFLICT_REQUIRES_REVIEW

    with pytest.raises(ConflictException):
        await service.verify(user_id, conflicting.id)


@pytest.mark.asyncio
async def test_get_with_wrong_owner_raises_forbidden() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    record = await service.create_from_extraction(
        user_id=user_id, record_type_code="ALLERGY", data={"substance": "Penicillin"}
    )

    with pytest.raises(ForbiddenException):
        await service.get(other_user_id, record.id)


@pytest.mark.asyncio
async def test_get_missing_record_raises_not_found() -> None:
    service = _service([_allergy_type()])

    with pytest.raises(NotFoundException):
        await service.get(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_list_data_by_type_excludes_rejected_but_keeps_other_statuses() -> None:
    allergy_type = _allergy_type()
    service = _service([allergy_type])
    user_id = uuid.uuid4()

    kept_statuses = [
        RecordStatus.NEEDS_REVIEW,
        RecordStatus.USER_EDITED,
        RecordStatus.VERIFIED,
        RecordStatus.CONFLICT_REQUIRES_REVIEW,
    ]
    for status in kept_statuses:
        await service.repo.create(
            MedicalRecord(
                id=uuid.uuid4(),
                user_id=user_id,
                record_type_id=allergy_type.id,
                status=status,
                data={"substance": status.value},
                current_version=1,
            )
        )
    await service.repo.create(
        MedicalRecord(
            id=uuid.uuid4(),
            user_id=user_id,
            record_type_id=allergy_type.id,
            status=RecordStatus.REJECTED,
            data={"substance": "rejected"},
            current_version=1,
        )
    )

    records = await service.list_data_by_type(user_id, "ALLERGY")

    assert {r.status for r in records} == set(kept_statuses)
