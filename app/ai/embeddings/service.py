from openai import AsyncOpenAI

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not settings.openai_api_key:
            return [[0.0] * settings.embedding_dimensions for _ in texts]
        response = await self.client.embeddings.create(model=settings.embedding_model, input=texts)
        return [item.embedding for item in response.data]
