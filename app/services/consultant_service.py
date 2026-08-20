import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.consultant.service import ConsultantAIService
from app.core.exceptions import NotFoundException, ValidationException
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import ChatContextType, MessageRole
from app.models.vitals import Vitals
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.consultant import ConversationListResponse
from app.services.document_record_service import DocumentRecordService
from app.services.medical_record_service import MedicalRecordService
from app.services.vitals_service import VitalsService

MAX_DOCUMENTS = 20
MAX_CHARS_PER_DOCUMENT = 4000
MAX_CHARS_GROUNDED_CONTEXT = 12000


class ConsultantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.user_repo = UserRepository(session)
        self.record_service = MedicalRecordService(session)
        self.document_record_service = DocumentRecordService(session)
        self.document_repo = DocumentRepository(session)
        self.analysis_repo = AnalysisRepository(session)
        self.vitals_service = VitalsService(session)
        self.ai = ConsultantAIService()

    async def ask(
        self,
        user_id: uuid.UUID,
        question: str,
        session_id: uuid.UUID | None = None,
        context_type: ChatContextType | None = None,
        context_id: uuid.UUID | None = None,
    ) -> dict:
        chat_session = None
        if session_id:
            chat_session = await self.chat_repo.get_session(user_id, session_id)

        if chat_session is None:
            chat_session = await self._create_session(user_id, question, context_type, context_id)

        self.session.add(
            ChatMessage(session_id=chat_session.id, role=MessageRole.USER, content=question, confidence=1.0)
        )

        if chat_session.context_type == ChatContextType.DOCUMENT:
            patient_context = await self._build_document_context(user_id, chat_session.context_id)
        elif chat_session.context_type == ChatContextType.ANALYSIS_RESULT:
            patient_context = await self._build_analysis_context(user_id, chat_session.context_id)
        else:
            patient_context = await self._build_patient_context(user_id)

        result = await self.ai.answer(question, patient_context)

        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role=MessageRole.ASSISTANT,
            content=result.get("answer", ""),
            confidence=float(result.get("confidence", 0.0)),
            citations=result.get("citations", []),
            warning=result.get("warning"),
        )
        self.session.add(assistant_msg)
        await self.session.commit()

        return {
            "session_id": str(chat_session.id),
            "answer": assistant_msg.content,
            "confidence": assistant_msg.confidence,
            "citations": assistant_msg.citations,
            "warning": assistant_msg.warning,
            "context_type": chat_session.context_type,
            "context_label": chat_session.context_label,
        }

    async def _create_session(
        self,
        user_id: uuid.UUID,
        question: str,
        context_type: ChatContextType | None,
        context_id: uuid.UUID | None,
    ) -> ChatSession:
        if (context_type is None) != (context_id is None):
            raise ValidationException("context_id is required when context_type is set")

        title = f"Consultant: {question[:50]}"
        context_label: str | None = None

        if context_type == ChatContextType.DOCUMENT:
            document = await self.document_repo.get_by_user_and_id(user_id, context_id)
            if document is None:
                raise NotFoundException("Selected document was not found.")
            if not (document.embedding_text or document.ocr_text):
                raise ValidationException(
                    "Selected document has no extracted text yet and cannot be used to ground a conversation."
                )
            context_label = document.file_name
            title = f"Chat about {document.file_name}"
        elif context_type == ChatContextType.ANALYSIS_RESULT:
            analysis = await self.analysis_repo.get_by_user_and_id(user_id, context_id)
            if analysis is None:
                raise NotFoundException("Selected analysis result was not found.")
            context_label = analysis.title
            title = f"Chat about {analysis.title}"

        chat_session = ChatSession(
            user_id=user_id,
            title=title,
            context_type=context_type,
            context_id=context_id,
            context_label=context_label,
        )
        await self.chat_repo.create(chat_session)
        await self.session.flush()
        await self.session.refresh(chat_session)
        return chat_session

    async def history(self, user_id: uuid.UUID, session_id: uuid.UUID) -> list[ChatMessage]:
        chat_session = await self.chat_repo.get_session(user_id, session_id)
        return chat_session.messages if chat_session else []

    async def list_sessions(self, user_id: uuid.UUID) -> list[ConversationListResponse]:
        sessions = await self.chat_repo.list_sessions(user_id)
        return [
            ConversationListResponse(
                title=s.title,
                session_id=s.id,
                updated_at=s.updated_at,
                context_type=s.context_type,
                context_label=s.context_label,
            )
            for s in sessions
        ]

    async def _build_document_context(self, user_id: uuid.UUID, document_id: uuid.UUID) -> str:
        document = await self.document_repo.get_by_user_and_id(user_id, document_id)
        if document is None:
            raise NotFoundException("Grounding document is no longer available.")
        text = (document.embedding_text or document.ocr_text or "")[:MAX_CHARS_GROUNDED_CONTEXT]
        return (
            "You are answering questions grounded ONLY in the following medical document. "
            "Do not use other patient records.\n\n"
            f"[document_id={document.id} file={document.file_name}]\n{text}"
        )

    async def _build_analysis_context(self, user_id: uuid.UUID, analysis_id: uuid.UUID) -> str:
        analysis = await self.analysis_repo.get_by_user_and_id(user_id, analysis_id)
        if analysis is None:
            raise NotFoundException("Grounding analysis result is no longer available.")
        timeline_lines = "\n".join(
            f"  - {item.get('date', 'unknown date')}: {item.get('finding', '')}" for item in (analysis.timeline or [])
        )
        evidence_lines = "\n".join(f"  - {item.get('snippet', '')}" for item in (analysis.evidence or []))
        body = (
            f"Title: {analysis.title}\n"
            f"Category: {analysis.category}\n"
            f"Risk Level: {analysis.risk_level}\n"
            f"Description: {analysis.description}\n"
            f"Clinical Reason: {analysis.clinical_reason}\n"
            f"Recommendation: {analysis.recommendation}\n"
            + (f"Timeline:\n{timeline_lines}\n" if timeline_lines else "")
            + (f"Evidence:\n{evidence_lines}\n" if evidence_lines else "")
        )[:MAX_CHARS_GROUNDED_CONTEXT]
        return (
            "You are answering questions grounded ONLY in the following analysis result. "
            "Do not use other patient records.\n\n"
            f"[analysis_result_id={analysis.id}]\n{body}"
        )

    async def _build_patient_context(self, user_id: uuid.UUID) -> str:
        user = await self.user_repo.get(user_id)
        latest_vitals = await self.vitals_service.get_latest(user_id)
        allergies = [
            *await self.record_service.list_data_by_type(user_id, "ALLERGY"),
            *await self.document_record_service.list_records(user_id, record_type_code="ALLERGY"),
        ]
        vaccinations = [
            *await self.record_service.list_data_by_type(user_id, "VACCINATION"),
            *await self.document_record_service.list_records(user_id, record_type_code="VACCINATION"),
        ]
        surgeries = [
            *await self.record_service.list_data_by_type(user_id, "SURGERY"),
            *await self.document_record_service.list_records(user_id, record_type_code="SURGERY"),
        ]
        documents = await self.document_repo.list_by_user(user_id)

        sections: list[str] = [self._format_profile(user, latest_vitals)]

        sections.append(self._format_allergies(allergies))
        sections.append(self._format_vaccinations(vaccinations))
        sections.append(self._format_surgeries(surgeries))
        sections.append(self._format_documents(documents))

        return "\n\n".join(sections)

    def _format_profile(self, user, vitals: Vitals | None) -> str:
        if user is None:
            return "Patient Profile: unavailable"
        age = self._calculate_age(user.date_of_birth)
        lines = [
            "Patient Profile:",
            f"- Age: {age if age is not None else 'unknown'}",
            f"- Height: {vitals.height if vitals and vitals.height is not None else 'unknown'}",
            f"- Weight: {vitals.weight if vitals and vitals.weight is not None else 'unknown'}",
            f"- Blood Group: {vitals.blood_group if vitals and vitals.blood_group else 'unknown'}",
            f"- Blood Pressure: {vitals.pressure if vitals and vitals.pressure else 'unknown'}",
            f"- Blood Sugar: {vitals.blood_sugar if vitals and vitals.blood_sugar is not None else 'unknown'}",
        ]
        if user.bio:
            lines.append(f"- Bio: {user.bio}")
        if user.notes:
            lines.append(f"- Notes: {user.notes}")
        return "\n".join(lines)

    @staticmethod
    def _calculate_age(date_of_birth: date | None) -> int | None:
        if date_of_birth is None:
            return None
        today = datetime.now(UTC).date()
        years = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            years -= 1
        return years

    def _format_allergies(self, allergies) -> str:
        if not allergies:
            return "Known Allergies: none recorded"
        lines = [
            f"- {a.data.get('substance')} (reaction: {a.data.get('reaction') or 'unknown'}, "
            f"severity: {a.data.get('severity') or 'unknown'})"
            for a in allergies
        ]
        return "Known Allergies:\n" + "\n".join(lines)

    def _format_vaccinations(self, vaccinations) -> str:
        if not vaccinations:
            return "Vaccination History: none recorded"
        lines = []
        for v in vaccinations:
            administered = v.data.get("date_administered")
            line = f"- {v.data.get('name')} administered {datetime.fromisoformat(administered).date() if administered else 'unknown date'}"
            next_due = v.data.get("next_due_date")
            if v.data.get("is_next_due") and next_due:
                line += f", next due {datetime.fromisoformat(next_due).date()}"
            lines.append(line)
        return "Vaccination History:\n" + "\n".join(lines)

    def _format_surgeries(self, surgeries) -> str:
        if not surgeries:
            return "Surgery History: none recorded"
        lines = [
            f"- {s.data.get('name')} on {s.data.get('date')}"
            + (f" (notes: {s.data.get('notes')})" if s.data.get("notes") else "")
            for s in surgeries
        ]
        return "Surgery History:\n" + "\n".join(lines)

    def _format_documents(self, documents) -> str:
        doc_texts = [d for d in documents if d.embedding_text][:MAX_DOCUMENTS]
        if not doc_texts:
            return "Medical Document Extracts: none available"
        lines = [
            f"[document_id={d.id} file={d.file_name}]\n{(d.embedding_text or '')[:MAX_CHARS_PER_DOCUMENT]}"
            for d in doc_texts
        ]
        return "Medical Document Extracts:\n" + "\n\n".join(lines)
