import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.record_intake.service import RecordIntakeAIService
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.enums import IntakeStatus
from app.models.medical_record import MedicalRecord
from app.models.record_intake_session import RecordIntakeSession
from app.models.record_type import RecordType
from app.repositories.record_intake_repository import RecordIntakeRepository
from app.services.medical_record_service import MedicalRecordService
from app.services.record_type_service import RecordTypeService

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 2


class RecordIntakeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecordIntakeRepository(session)
        self.record_type_service = RecordTypeService(session)
        self.medical_record_service = MedicalRecordService(session)
        self.ai = RecordIntakeAIService()

    async def start(self, user_id: uuid.UUID, text: str) -> RecordIntakeSession:
        known_record_types = await self.record_type_service.list_active()
        known_record_types_payload = [
            {
                "code": record_type.code,
                "name": record_type.name,
                "description": record_type.description,
                "identity_field": record_type.identity_field,
                "schema": record_type.json_schema,
            }
            for record_type in known_record_types
        ]

        classification = await self.ai.classify_single(text, known_record_types_payload)
        record_type = await self._resolve_record_type(classification)

        result = await self.ai.extract_and_ask(text, record_type, {}, [])

        intake = RecordIntakeSession(
            user_id=user_id,
            raw_text=text,
            record_type_id=record_type.id,
            is_new_record_type=bool(classification.get("is_new_type")),
            classification_confidence=classification.get("confidence"),
            questions_asked=0,
        )
        self._apply_ai_result(intake, result)

        await self.repo.create(intake)
        await self.session.commit()
        return intake

    async def _resolve_record_type(self, classification: dict) -> RecordType:
        code = str(classification.get("record_type_code") or "").strip().upper()
        if classification.get("is_new_type"):
            if not code:
                raise ValidationException("Could not classify the provided text into a record type")
            return await self.record_type_service.get_or_create(
                code=code,
                name=classification.get("name") or code.replace("_", " ").title(),
                description=classification.get("description"),
                json_schema=classification.get("json_schema")
                or {"type": "object", "properties": {}, "additionalProperties": True},
                identity_field=classification.get("identity_field"),
            )

        if not code:
            raise ValidationException("Could not classify the provided text into a record type")
        return await self.record_type_service.get_by_code(code)

    def _apply_ai_result(self, intake: RecordIntakeSession, result: dict) -> None:
        intake.draft_data = result.get("data") or {}
        intake.missing_fields = result.get("missing_fields") or []
        next_question = result.get("next_question")

        if next_question and intake.missing_fields and intake.questions_asked < MAX_QUESTIONS:
            intake.status = IntakeStatus.AWAITING_CLARIFICATION
            intake.pending_field = intake.missing_fields[0]
            intake.pending_question = next_question
        else:
            intake.status = IntakeStatus.AWAITING_CONFIRMATION
            intake.pending_field = None
            intake.pending_question = None

    async def get(self, user_id: uuid.UUID, intake_id: uuid.UUID) -> RecordIntakeSession:
        return await self._get_owned(user_id, intake_id)

    async def answer(self, user_id: uuid.UUID, intake_id: uuid.UUID, answer_text: str) -> RecordIntakeSession:
        intake = await self._get_owned(user_id, intake_id)
        if intake.status != IntakeStatus.AWAITING_CLARIFICATION:
            raise ConflictException(f"Cannot answer an intake session in status '{intake.status.value}'")

        intake.answers = [
            *intake.answers,
            {"field": intake.pending_field, "question": intake.pending_question, "answer": answer_text},
        ]
        intake.questions_asked += 1

        record_type = await self.record_type_service.get_by_id(intake.record_type_id)
        result = await self.ai.extract_and_ask(intake.raw_text, record_type, intake.draft_data, intake.answers)
        self._apply_ai_result(intake, result)

        if intake.questions_asked >= MAX_QUESTIONS:
            intake.status = IntakeStatus.AWAITING_CONFIRMATION
            intake.pending_field = None
            intake.pending_question = None

        await self.session.commit()
        return intake

    async def confirm(
        self, user_id: uuid.UUID, intake_id: uuid.UUID, data_overrides: dict[str, Any] | None
    ) -> MedicalRecord:
        intake = await self._get_owned(user_id, intake_id)
        if intake.status != IntakeStatus.AWAITING_CONFIRMATION:
            raise ConflictException(f"Cannot confirm an intake session in status '{intake.status.value}'")

        final_data = {**intake.draft_data, **(data_overrides or {})}
        record_type = await self.record_type_service.get_by_id(intake.record_type_id)
        final_data = self._filter_data_to_schema(record_type, final_data)
        self.record_type_service.validate_data(record_type, final_data)

        record = await self.medical_record_service.create_from_extraction(
            user_id=user_id,
            record_type_code=record_type.code,
            data=final_data,
            recorded_at=intake.recorded_at,
        )
        if record is None:
            raise NotFoundException("Record type no longer available")

        intake.status = IntakeStatus.COMPLETED
        intake.resulting_record_id = record.id
        intake.draft_data = final_data

        await self.session.commit()

        # The user just walked through the confirm step for this exact data, which is
        # itself a trust signal (unlike a freshly-OCR'd document record still awaiting
        # review) - so embed immediately rather than waiting for a separate verify().
        try:
            await self.medical_record_service.embedding_service.embed_medical_record(
                user_id, record, record_type
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Embedding failed for intake-confirmed record %s", record.id)

        return record

    async def abandon(self, user_id: uuid.UUID, intake_id: uuid.UUID) -> RecordIntakeSession:
        intake = await self._get_owned(user_id, intake_id)
        if intake.status == IntakeStatus.COMPLETED:
            raise ConflictException("Cannot abandon a completed intake session")

        intake.status = IntakeStatus.ABANDONED
        await self.session.commit()
        return intake

    async def _get_owned(self, user_id: uuid.UUID, intake_id: uuid.UUID) -> RecordIntakeSession:
        intake = await self.repo.get(intake_id)
        if intake is None:
            raise NotFoundException("Intake session not found")
        if intake.user_id != user_id:
            raise ForbiddenException("You do not have access to this intake session")
        return intake

    @staticmethod
    def _filter_data_to_schema(record_type: RecordType, data: dict) -> dict:
        schema = record_type.json_schema or {}
        if schema.get("additionalProperties") is False:
            allowed_fields = set(schema.get("properties", {}))
            return {key: value for key, value in data.items() if key in allowed_fields}
        return data
