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

        logger.debug("OpenAI response received (%d chars)", len(response.output_text or ""))

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
            # Never log the content itself: it is patient health data.
            logger.error("Unparseable OpenAI response (%d chars)", len(response.output_text or ""))
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
    
            logger.debug("OpenAI response received (%d chars)", len(response.output_text or ""))
    
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
                # Never log the content itself: it is patient health data.
                logger.error("Unparseable OpenAI response (%d chars)", len(response.output_text or ""))
                return []
    

    async def classify_extraction_result(
        self,
        extraction_result: dict,
        known_record_types: list[dict],
    ) -> list[dict]:
        prompt = f"""
            You are a medical records classification assistant.

            You are given:
            1. A free-form JSON object extracted from a medical document (field names and
               structure were decided freely and are not standardized).
            2. A list of known medical record types, each with a code, description, and a
               strict JSON Schema describing the exact fields a record of that type holds.

            Break the free-form extraction down into individual discrete medical records
            (one entry per medication, lab result, allergy, diagnosis, vaccination,
            condition, procedure, surgery, family history entry, etc.) and classify each
            one.

            STRICT RULES:
            - Return only valid JSON.
            - For each discrete record you find, choose the best-fitting "record_type_code"
              from the known record types list.
            - Only set "is_new_type" to true if NONE of the known record types reasonably
              fit. When true, invent a new short UPPER_SNAKE_CASE code that does not
              collide with any known code, plus "name", "description", a strict JSON
              Schema ("json_schema" - an object with "type": "object", "properties", the
              always-present fields listed in "required", and "additionalProperties":
              false), and "identity_field" (the field name used to detect duplicates of
              this record type, or null).
            - When using an existing record_type_code, set "is_new_type" to false and
              leave "name", "description", "json_schema", "identity_field" as null.
            - "data" must be an object whose keys are a subset of the target record
              type's schema properties (the existing type's schema, or your proposed
              json_schema for a new type).
            - Do not create records for patient identity, doctor, hospital, or visit-level
              metadata - that is captured separately.
            - Do not guess or hallucinate information that is not present in the source.
            - Use null when information is missing.
            - "recorded_at" is the most clinically relevant date for the record (e.g.
              observed date, start date, date administered) as "YYYY-MM-DD", or null.
            - Skip anything you cannot confidently classify or that has no real data.

            Known record types:
            {json.dumps(known_record_types, indent=2, default=str)}

            Free-form extraction:
            {json.dumps(extraction_result, indent=2, default=str)}

            Return JSON exactly like this:

            {{
              "records": [
                {{
                  "record_type_code": "MEDICATION",
                  "is_new_type": false,
                  "name": null,
                  "description": null,
                  "json_schema": null,
                  "identity_field": null,
                  "data": {{"name": "Metformin", "dosage": "500mg"}},
                  "recorded_at": "2024-05-01"
                }}
              ]
            }}

            If nothing is found:

            {{"records": []}}
            """

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_SAFETY_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            text={"format": {"type": "json_object"}},
        )

        try:
            data = json.loads(response.output_text)
            records = data.get("records", []) if isinstance(data, dict) else []
            if not isinstance(records, list):
                return []
            return [record for record in records if isinstance(record, dict)]
        except json.JSONDecodeError:
            logger.exception("Failed to parse OpenAI response")
            # Never log the content itself: it is patient health data.
            logger.error("Unparseable OpenAI response (%d chars)", len(response.output_text or ""))
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
