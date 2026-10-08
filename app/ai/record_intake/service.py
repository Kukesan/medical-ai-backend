import json
from datetime import date

from fastapi.logger import logger
from openai import AsyncOpenAI

from app.ai.prompts.safety import SYSTEM_SAFETY_PROMPT
from app.core.config import settings
from app.models.record_type import RecordType


class RecordIntakeAIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def classify_single(self, text: str, known_record_types: list[dict]) -> dict:
        prompt = f"""
            You are a medical records classification assistant.

            You are given:
            1. Free text a patient typed describing a single medical event or fact
               (e.g. an injury, a symptom, an allergy, a vaccination).
            2. A list of known medical record types, each with a code, description, and a
               strict JSON Schema describing the exact fields a record of that type holds.

            Classify the text as ONE record of ONE record type.

            STRICT RULES:
            - Return only valid JSON.
            - Choose the best-fitting "record_type_code" from the known record types list.
            - Only set "is_new_type" to true if NONE of the known record types reasonably
              fit. When true, invent a new short UPPER_SNAKE_CASE code that does not
              collide with any known code, plus "name", "description", a strict JSON
              Schema ("json_schema" - an object with "type": "object", "properties", the
              always-present fields listed in "required", and "additionalProperties":
              false), and "identity_field" (the field name used to detect duplicates of
              this record type, or null).
            - When using an existing record_type_code, set "is_new_type" to false and
              leave "name", "description", "json_schema", "identity_field" as null.
            - "confidence" is your confidence in this classification, from 0.0 to 1.0.
            - Do not guess or hallucinate information that is not present in the text.

            Known record types:
            {json.dumps(known_record_types, indent=2, default=str)}

            Patient text:
            {text[:20000]}

            Return JSON exactly like this:

            {{
              "record_type_code": "ALLERGY",
              "is_new_type": false,
              "confidence": 0.86,
              "name": null,
              "description": null,
              "json_schema": null,
              "identity_field": null
            }}
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
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.exception("Failed to parse OpenAI classification response")
            # Never log the content itself: it is patient health data.
            logger.error("Unparseable OpenAI response (%d chars)", len(response.output_text or ""))
            return {}

    async def extract_and_ask(
        self,
        original_text: str,
        record_type: RecordType,
        draft_data: dict,
        qa_history: list[dict],
    ) -> dict:
        prompt = f"""
            You are a medical intake assistant helping a patient record a single medical
            event as a structured record.

            You are given:
            1. The record type this event was classified as, with its name, description,
               and JSON Schema (the "required" fields are the important fields to fill).
            2. The patient's original free text.
            3. Any follow-up questions already asked and the patient's answers.

    Re-derive the structured data from scratch using ALL of the information above
            (the original text plus every question/answer pair), then identify which of
            the schema's important fields are still missing, and - if any are missing -
            write ONE natural-language follow-up question that would fill the single most
            important missing field.

            You must also determine "recorded_at": the single calendar date this event
            actually happened (not when the patient is typing it in), as a strict ISO
            8601 date "YYYY-MM-DD".

            STRICT RULES:
            - Return only valid JSON.
            - "data" must be an object whose keys are a subset of the record type's schema
              properties.
            - Do not guess or hallucinate information not present in the text or answers.
            - Use null for a field only when it is genuinely absent from all context.
            - "missing_fields" lists the schema's important/required fields that are still
              unfilled in "data" (empty list if none).
            - "next_question" is a short, natural, single question about the single most
              important entry in "missing_fields", or null if "missing_fields" is empty.
            - Ask about only ONE field at a time.
            - Today's date is {date.today().isoformat()}. Use it to resolve relative
              dates ("yesterday", "last Tuesday", "three weeks ago") into an exact
              calendar date.
            - If the text gives no date at all, set "recorded_at" to null and do NOT ask
              about it - absence of a date is not ambiguity.
            - If the text mentions a date but it is ambiguous, incomplete, or internally
              inconsistent (e.g. only a month/year, conflicting mentions, an impossible
              date) such that you cannot confidently resolve it to one exact calendar
              date, set "recorded_at" to null, add "recorded_at" to "missing_fields", and
              - if it is the most important gap - make "next_question" ask the patient to
              confirm the exact date.

            Record type: {record_type.name} ({record_type.code})
            Description: {record_type.description or "n/a"}
            JSON Schema:
            {json.dumps(record_type.json_schema, indent=2, default=str)}

            Patient's original text:
            {original_text[:20000]}

            Current draft data:
            {json.dumps(draft_data, indent=2, default=str)}

            Follow-up question/answer history:
            {json.dumps(qa_history, indent=2, default=str)}

            Return JSON exactly like this:

            {{
              "data": {{"...": "..."}},
              "missing_fields": ["incident_date"],
              "next_question": "When did this happen?",
              "recorded_at": "2026-08-14"
            }}
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
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.exception("Failed to parse OpenAI extract_and_ask response")
            # Never log the content itself: it is patient health data.
            logger.error("Unparseable OpenAI response (%d chars)", len(response.output_text or ""))
            return {}
