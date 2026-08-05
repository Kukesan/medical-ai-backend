from openai import AsyncOpenAI
from app.core.config import settings

class EmbeddingsFormatterService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def format_text_for_embedding(self, text: str) -> str:
        prompt = f"""
            You are an expert medical document normalization assistant.

            Your task is to convert noisy OCR text into clean, meaningful text optimized for semantic embeddings.

            Rules:

            1. Preserve ALL information.
            - Do not summarize.
            - Do not remove medical facts.
            - Do not invent missing information.

            2. Fix OCR formatting.
            - Remove duplicated spaces.
            - Remove unnecessary line breaks.
            - Merge broken sentences.
            - Remove repeated headers, footers, page numbers, and OCR artifacts.

            3. Preserve medical terminology exactly.
            - Keep medicine names unchanged.
            - Keep diagnosis names unchanged.
            - Keep laboratory values exactly.
            - Preserve units (mg, ml, mmol/L, %, etc.).
            - Preserve dates and times.

            4. Organize information logically.
            Example sections:
            - Patient Information
            - Visit Information
            - Chief Complaint
            - History
            - Diagnosis
            - Medications
            - Laboratory Results
            - Instructions
            - Follow-up

            Only include sections that exist.

            5. If text is already clean, return it unchanged.

            6. Output only the cleaned text.
            Do not add explanations.
            Do not use Markdown.
            Do not include JSON.

            OCR Text:

            {text}
            """

        response = await self.client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You normalize OCR medical documents into clean semantic text "
                        "optimized for vector embeddings while preserving every fact."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
            text={"format": {"type": "text"}},
        )

        return response.output_text.strip()