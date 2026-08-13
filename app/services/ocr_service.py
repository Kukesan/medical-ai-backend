from pathlib import Path

from app.ai.extraction.ocr_service import get_ocr_service


class OCRService:
    def __init__(self) -> None:
        self.impl = get_ocr_service()

    async def process(self, file_path: Path) -> dict:
        return await self.impl.extract_text(file_path)
