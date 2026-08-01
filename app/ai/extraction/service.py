import json

from openai import AsyncOpenAI

from app.ai.prompts.safety import SYSTEM_SAFETY_PROMPT
from app.core.config import settings


class ExtractionService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_structured(self, ocr_text: str) -> dict:
        if not settings.openai_api_key:
            return self._empty_response()

        prompt = (
            "Extract structured medical info from this OCR text. "
            "Only include diagnosis if explicitly present. "
            "Return strict JSON with confidence per field.\n\n"
            f"OCR:\n{ocr_text[:100000]}"
        )

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_SAFETY_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            text={"format": {"type": "text"}},
        )

        raw = response.output_text
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._empty_response()

    def _empty_response(self) -> dict:
        return {
            "visit_date": None,
            "doctor": None,
            "hospital": None,
            "medications": [],
            "lab_results": [],
            "diagnosis_if_explicit": None,
            "allergies": [],
            "clinical_notes": [],
            "confidence": 0.0,
        }
