import json

from openai import AsyncOpenAI

from app.ai.prompts.safety import SYSTEM_SAFETY_PROMPT
from app.core.config import settings
from pydantic import BaseModel
from typing import Type
import json

class ExtractionService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)


    async def extract_to_schema(
        self,
        ocr_text: str,
        schema: Type[BaseModel]
    ) -> dict:

        schema_json = schema.model_json_schema()

        prompt = f"""
    You are a medical information extraction assistant.

    Extract information from the OCR text and map it to the target schema.

    STRICT RULES:
    - Return only valid JSON.
    - Follow the target schema exactly.
    - Do not add fields outside the schema.
    - Do not guess or hallucinate information.
    - Use null when information is missing.
    - Only include diagnosis if explicitly mentioned.

    Target schema:
    {json.dumps(schema_json, indent=2)}

    OCR Text:
    {ocr_text[:100000]}
    """
        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_SAFETY_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            text={"format": {"type": "json_object"}},
        )
        try:
            return json.loads(response.output_text)

        except json.JSONDecodeError:
            return {}


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
