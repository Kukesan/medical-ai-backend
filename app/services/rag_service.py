from app.ai.rag.service import RAGService as AIRAGService


class RAGService:
    def __init__(self) -> None:
        self.impl = AIRAGService()

    async def answer(self, question: str, chunks: list[dict]) -> dict:
        return await self.impl.answer(question, chunks)
