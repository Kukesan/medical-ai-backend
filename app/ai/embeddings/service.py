from openai import AsyncOpenAI

from app.ai.embeddings.faiss_store import FaissStore
from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.store = FaissStore()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not settings.openai_api_key:
            return [[0.0] * 1536 for _ in texts]
        response = await self.client.embeddings.create(model=settings.embedding_model, input=texts)
        return [item.embedding for item in response.data]

    async def add_chunks(self, chunks: list[str], metadatas: list[dict]) -> list[int]:
        vectors = await self.embed_texts(chunks)
        return self.store.add(vectors, metadatas)

    async def similarity_search(self, question: str, top_k: int = 5) -> list[dict]:
        query_vec = (await self.embed_texts([question]))[0]
        return self.store.search(query_vec, top_k=top_k)
