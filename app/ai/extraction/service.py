import json

from fastapi.logger import logger
from openai import AsyncOpenAI

from app.ai.prompts.safety import SYSTEM_SAFETY_PROMPT
from app.core.config import settings
from pydantic import BaseModel, schema
from typing import Type, TypeVar

T = TypeVar("T", bound=BaseModel)
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
        

    async def extract_to_schema_free(
        self,
        ocr_text: str,
    ) -> dict:

        prompt = f"""
            You are a medical information extraction assistant.

            Extract all relevant structured information from the OCR text.
            Decide the JSON field names and structure yourself based on what
            is actually present in the text.

            STRICT RULES:
            - Return only valid JSON.
            - Do not guess or hallucinate information.
            - Use null when information is missing.
            - Only include diagnosis if explicitly mentioned.

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


   
    async def extract_to_schema_list(
        self,
        ocr_text: str,
        schema: Type[T],
    ) -> list[T]:

        schema_json = schema.model_json_schema()

        prompt = f"""
            You are a medical information extraction assistant.

            Extract ALL matching records from the OCR text.

            STRICT RULES:
            - Return ONLY a valid JSON object.
            - The JSON object MUST contain an "items" array.
            - Every object inside "items" must follow the target schema exactly.
            - Do not add fields outside the schema.
            - Do not guess or hallucinate information.
            - Use null when information is missing.
            - Return an empty array if nothing is found.

            Target schema:
            {json.dumps(schema_json, indent=2)}

            Return JSON exactly like this:

            {{
            "items": [
                {{
                "...": "..."
                }}
            ]
            }}

            If nothing is found:

            {{
            "items": []
            }}

            OCR Text:
            {ocr_text[:100000]}
            """

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_SAFETY_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            text={"format": {"type": "json_object"}},
        )

        logger.info("OpenAI Response: %s", response.output_text)

        try:
            data = json.loads(response.output_text)

            if not isinstance(data, dict):
                logger.warning("Expected JSON object but got: %s", type(data))
                return []

            items = data.get("items", [])

            if not isinstance(items, list):
                logger.warning("'items' is not a list")
                return []

            return [schema.model_validate(item) for item in items]

        except Exception as e:
            logger.exception("Failed to parse OpenAI response")
            logger.error("Raw response: %s", response.output_text)
            return []


    async def extract_to_schema_list_free(
            self,
            ocr_text: str,
        ) -> list[dict]:
    
            prompt = f"""
                You are a medical information extraction assistant.
    
                Extract ALL matching records from the OCR text.
                Decide the JSON field names and structure yourself based on what
                is actually present in the text.
    
                STRICT RULES:
                - Return ONLY a valid JSON object.
                - The JSON object MUST contain an "items" array.
                - Do not guess or hallucinate information.
                - Use null when information is missing.
                - Return an empty array if nothing is found.
    
                Return JSON exactly like this:
    
                {{
                "items": [
                    {{
                    "...": "..."
                    }}
                ]
                }}
    
                If nothing is found:
    
                {{
                "items": []
                }}
    
                OCR Text:
                {ocr_text[:100000]}
                """
    
            response = await self.client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": SYSTEM_SAFETY_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
                text={"format": {"type": "json_object"}},
            )
    
            logger.info("OpenAI Response: %s", response.output_text)
    
            try:
                data = json.loads(response.output_text)
    
                if not isinstance(data, dict):
                    logger.warning("Expected JSON object but got: %s", type(data))
                    return []
    
                items = data.get("items", [])
    
                if not isinstance(items, list):
                    logger.warning("'items' is not a list")
                    return []
    
                return items
    
            except Exception:
                logger.exception("Failed to parse OpenAI response")
                logger.error("Raw response: %s", response.output_text)
                return []
    

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
