from app.ai.extraction.service import ExtractionService as AIExtractionService


class ExtractionService:
    def __init__(self) -> None:
        self.impl = AIExtractionService()

    async def run(self, text: str) -> dict:
        return await self.impl.extract_structured(text)
