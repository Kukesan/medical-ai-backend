import json

from openai import AsyncOpenAI

from app.ai.prompts.consultant import SYSTEM_MEDICAL_CONSULTANT_PROMPT
from app.core.config import settings


class ConsultantAIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def answer(self, question: str, patient_context: str) -> dict:
        if not settings.openai_api_key:
            return {
                "answer": "Unable to generate AI answer because OpenAI key is not configured.",
                "confidence": 0.0,
                "citations": [],
                "warning": "Please configure AI provider and consult a healthcare professional for decisions.",
            }

        instruction = (
            "Answer the patient's question using only the patient context provided below. "
            "Return JSON with keys: answer, confidence, citations, warning. "
            "Each citation must be an object with keys source_document_id, snippet, and "
            "optionally page. Use values such as 'profile', 'allergy', 'vaccination', "
            "'surgery', or the medical document id as source_document_id. "
            "Never diagnose and include a consultation warning for high risk or low confidence.\n\n"
            f"Question: {question}\n\nPatient Context:\n{patient_context}"
        )

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_MEDICAL_CONSULTANT_PROMPT},
                {"role": "user", "content": instruction},
            ],
            temperature=0.1,
            text={"format": {"type": "text"}},
        )

        raw = response.output_text
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "answer": "I could not confidently generate a grounded response.",
                "confidence": 0.2,
                "citations": [],
                "warning": "Please consult a healthcare professional.",
            }
