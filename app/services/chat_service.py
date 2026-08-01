import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import MessageRole
from app.repositories.chat_repository import ChatRepository
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import RAGService


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ChatRepository(session)
        self.embedding = EmbeddingService(session)
        self.rag = RAGService()

    async def ask(self, user_id: uuid.UUID, question: str, session_id: uuid.UUID | None = None) -> dict:
        session = None
        if session_id:
            session = await self.repo.get_session(user_id, session_id)

        if session is None:
            session = ChatSession(user_id=user_id, title=question[:60])
            await self.repo.create(session)
            await self.session.flush()

        await self.session.flush()
        await self.session.refresh(session)

        await self.session.flush()
        self.session.add(
            ChatMessage(session_id=session.id, role=MessageRole.USER, content=question, confidence=1.0)
        )

        chunks = await self.embedding.search(question, top_k=5)
        answer = await self.rag.answer(question, chunks)

        assistant_msg = ChatMessage(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=answer.get("answer", ""),
            confidence=float(answer.get("confidence", 0.0)),
            citations=answer.get("citations", []),
            warning=answer.get("warning"),
        )
        self.session.add(assistant_msg)
        await self.session.commit()

        return {
            "session_id": str(session.id),
            "answer": assistant_msg.content,
            "confidence": assistant_msg.confidence,
            "citations": assistant_msg.citations,
            "warning": assistant_msg.warning,
        }

    async def history(self, user_id: uuid.UUID, session_id: uuid.UUID) -> list[ChatMessage]:
        session = await self.repo.get_session(user_id, session_id)
        return session.messages if session else []
