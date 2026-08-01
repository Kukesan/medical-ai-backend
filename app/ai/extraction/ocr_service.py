from pathlib import Path

from app.models.enums import DocumentType


class OCRService:
    async def extract_text(self, file_path: Path) -> dict:
        docling_result = await self._run_docling(file_path)
        if docling_result is not None:
            return docling_result

        paddle_result = await self._run_paddleocr(file_path)
        if paddle_result is not None:
            return paddle_result

        return {
            "text": "",
            "metadata": {
                "pages": [],
                "overall_confidence": 0.0,
                "document_type": DocumentType.OTHER,
                "engine": "none",
            },
        }

    async def _run_docling(self, file_path: Path) -> dict | None:
        try:
            from docling.document_converter import DocumentConverter
        except Exception:
            return None

        try:
            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            text = result.document.export_to_markdown()
            return {
                "text": text,
                "metadata": {
                    "pages": [{"page_number": 1, "confidence": 0.85}],
                    "overall_confidence": 0.85,
                    "document_type": DocumentType.OTHER,
                    "engine": "docling",
                },
            }
        except Exception:
            return None

    async def _run_paddleocr(self, file_path: Path) -> dict | None:
        try:
            from paddleocr import PaddleOCR
        except Exception:
            return None

        try:
            ocr = PaddleOCR(use_angle_cls=True, lang="en")
            result = ocr.ocr(str(file_path), cls=True)
            lines: list[str] = []
            confidences: list[float] = []
            for page in result:
                for item in page:
                    if not item or len(item) < 2:
                        continue
                    txt = item[1][0]
                    conf = float(item[1][1])
                    lines.append(txt)
                    confidences.append(conf)
            overall = sum(confidences) / len(confidences) if confidences else 0.0
            return {
                "text": "\n".join(lines),
                "metadata": {
                    "pages": [{"page_number": 1, "confidence": overall}],
                    "overall_confidence": overall,
                    "document_type": DocumentType.OTHER,
                    "engine": "paddleocr",
                },
            }
        except Exception:
            return None
