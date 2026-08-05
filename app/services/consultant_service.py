import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.consultant.service import ConsultantAIService
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import MessageRole
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.surgery_repository import SurgeryRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vaccination_repository import VaccinationRepository
from app.schemas.consultant import ConversationListResponse

MAX_DOCUMENTS = 20
MAX_CHARS_PER_DOCUMENT = 4000


class ConsultantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.user_repo = UserRepository(session)
        self.allergy_repo = AllergyRepository(session)
        self.vaccination_repo = VaccinationRepository(session)
        self.surgery_repo = SurgeryRepository(session)
        self.document_repo = DocumentRepository(session)
        self.ai = ConsultantAIService()

    async def ask(self, user_id: uuid.UUID, question: str, session_id: uuid.UUID | None = None) -> dict:
        chat_session = None
        if session_id:
            chat_session = await self.chat_repo.get_session(user_id, session_id)

        if chat_session is None:
            chat_session = ChatSession(user_id=user_id, title=f"Consultant: {question[:50]}")
            await self.chat_repo.create(chat_session)
            await self.session.flush()
            await self.session.refresh(chat_session)

        self.session.add(
            ChatMessage(session_id=chat_session.id, role=MessageRole.USER, content=question, confidence=1.0)
        )

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
        }

    async def history(self, user_id: uuid.UUID, session_id: uuid.UUID) -> list[ChatMessage]:
        chat_session = await self.chat_repo.get_session(user_id, session_id)
        return chat_session.messages if chat_session else []

    async def list_sessions(self, user_id: uuid.UUID) -> list[ConversationListResponse]:
        sessions = await self.chat_repo.list_sessions(user_id)
        return [
            ConversationListResponse(
                title=f"Conversation {i+1}",
                session_id=s.id,
                updated_at=s.updated_at,
            )
            for i, s in enumerate(sessions)
        ]

    async def _build_patient_context(self, user_id: uuid.UUID) -> str:
        user = await self.user_repo.get(user_id)
        allergies = await self.allergy_repo.list_by_user(user_id)
        vaccinations = await self.vaccination_repo.list_by_user(user_id)
        surgeries = await self.surgery_repo.list_by_user(user_id)
        documents = await self.document_repo.list_by_user(user_id)

        sections: list[str] = [self._format_profile(user)]

        sections.append(self._format_allergies(allergies))
        sections.append(self._format_vaccinations(vaccinations))
        sections.append(self._format_surgeries(surgeries))
        sections.append(self._format_documents(documents))

        return "\n\n".join(sections)

    def _format_profile(self, user) -> str:
        if user is None:
            return "Patient Profile: unavailable"
        return (
            "Patient Profile:\n"
            f"- Age: {user.age if user.age is not None else 'unknown'}\n"
            f"- Height: {user.height if user.height is not None else 'unknown'}\n"
            f"- Weight: {user.weight if user.weight is not None else 'unknown'}\n"
            f"- Blood Group: {user.blood_group or 'unknown'}\n"
            f"- Blood Pressure: {user.pressure or 'unknown'}\n"
            f"- Blood Sugar: {user.blood_sugar if user.blood_sugar is not None else 'unknown'}"
        )

    def _format_allergies(self, allergies) -> str:
        if not allergies:
            return "Known Allergies: none recorded"
        lines = [
            f"- {a.substance} (reaction: {a.reaction or 'unknown'}, severity: {a.severity or 'unknown'})"
            for a in allergies
        ]
        return "Known Allergies:\n" + "\n".join(lines)

    def _format_vaccinations(self, vaccinations) -> str:
        if not vaccinations:
            return "Vaccination History: none recorded"
        lines = []
        for v in vaccinations:
            line = f"- {v.name} administered {v.date_administered.date()}"
            if v.is_next_due and v.next_due_date:
                line += f", next due {v.next_due_date.date()}"
            lines.append(line)
        return "Vaccination History:\n" + "\n".join(lines)

    def _format_surgeries(self, surgeries) -> str:
        if not surgeries:
            return "Surgery History: none recorded"
        lines = [f"- {s.name} on {s.date}" + (f" (notes: {s.notes})" if s.notes else "") for s in surgeries]
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
