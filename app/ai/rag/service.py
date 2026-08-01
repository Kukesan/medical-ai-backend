import json

from openai import AsyncOpenAI

from app.ai.prompts.safety import SYSTEM_SAFETY_PROMPT
from app.core.config import settings


class RAGService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def answer(self, question: str, context_chunks: list[dict]) -> dict:
        context = "\n\n".join(
            [
                f"[source={c['metadata'].get('source_document_id', 'unknown')}] {c['metadata'].get('chunk_text', '')}"
                for c in context_chunks
            ]
        )

        if not settings.openai_api_key:
            return {
                "answer": "Unable to generate AI answer because OpenAI key is not configured.",
                "confidence": 0.0,
                "citations": [],
                "warning": "Please configure AI provider and consult a healthcare professional for decisions.",
            }

        instruction = (
            "Answer the user question using only the provided context. "
            "Return JSON with keys: answer, confidence, citations, warning. "
            "Never diagnose and include a consultation warning for high risk or low confidence.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_SAFETY_PROMPT},
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
