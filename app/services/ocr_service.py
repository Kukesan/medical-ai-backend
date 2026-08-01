from pathlib import Path

from app.ai.extraction.ocr_service import OCRService as AIExtractorOCRService


class OCRService:
    def __init__(self) -> None:
        self.impl = AIExtractorOCRService()

    async def process(self, file_path: Path) -> dict:
        return await self.impl.extract_text(file_path)
