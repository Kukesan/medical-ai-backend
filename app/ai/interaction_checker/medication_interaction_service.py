from app.schemas.medication_analyze import MedicalDocumentInput, MedicationReviewResult
from app.core.config import settings
from openai import AsyncOpenAI

class MedicationInteractionService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def build_medication_review_prompt(
        self,
        documents: list[MedicalDocumentInput]
    ) -> tuple[str, str]:

        system_prompt = """
            You are an expert clinical pharmacist and medication safety AI.

            You analyze multiple medical documents across time.

            Your goal is to identify medication safety concerns by comparing
            current and historical medical records.


            Perform these checks:


            1. Medication History Extraction

            Extract from all documents:

            - Medication name
            - Generic name
            - Strength
            - Dose
            - Frequency
            - Duration
            - Prescribed date
            - Prescribing document


            2. Duplicate Medication Detection

            Find:

            - Same medication in multiple prescriptions
            - Brand and generic duplicates
            - Duplicate active ingredients
            - Duplicate therapy

            Consider medication timeline.

            Example:

            January:
            Paracetamol 500mg

            February:
            Panadol 500mg

            Possible duplicate because both contain paracetamol.


            3. Medication Change Analysis

            Detect:

            - Dose increases
            - Dose decreases
            - New medications
            - Discontinued medications
            - Replacement medications


            4. Drug Interaction Analysis

            Check:

            - Current medication combinations
            - Historical medications still possibly active
            - High-risk interactions


            5. Dosage Conflict Detection

            Find:

            - Different doses for same medication
            - Conflicting instructions
            - Excessive daily dosage


            6. Allergy Safety Check

            Compare:

            - Allergies mentioned in any document
            - Prescribed medications


            7. Laboratory Trend Analysis

            Analyze lab values over time.

            Look for:

            - Kidney changes
            - Liver changes
            - Blood changes
            - Glucose changes

            Identify possible medication-related risks.


            RULES:

            - Do not diagnose diseases.
            - Do not recommend stopping medication.
            - Do not modify prescriptions.
            - Do not invent information.
            - Use only provided documents.
            - Mention uncertainty when information is incomplete.


            Return JSON only:

            {
            "overall_risk":"low|medium|high|critical",

            "summary":"",

            "alerts":[
            {
                "category":
                "drug_interaction |
                duplicate_medication |
                allergy_conflict |
                dosage_conflict |
                medication_change |
                lab_abnormality",

                "risk_level":"low|medium|high|critical",

                "title":"",

                "description":"",

                "clinical_reason":"",

                "confidence":0.0,

                "timeline":[
                {
                    "document_id":"",
                    "date":"",
                    "finding":""
                }
                ],

                "evidence":[
                {
                    "document_id":"",
                    "snippet":""
                }
                ],

                "recommendation":
                "Discuss with healthcare professional"
            }
            ]
            }

            """


        medical_history = "\n\n".join(
                    [
                        f"""
                            DOCUMENT ID:
                            {doc.document_id}

                            DATE:
                            {doc.document_date}

                            CONTENT:
                            {doc.ocr_text}
                            """
                        for doc in documents
                    ]
                )


        user_prompt = f"""

                            Review this patient's complete medical document history.

                            Medical Documents:

                            --------------------
                            {medical_history}
                            --------------------


                            Analyze medication safety across all documents.

                            Return JSON only.

                            """


        return system_prompt, user_prompt

    async def review_medication_history(
        self,
        documents: list[MedicalDocumentInput]
    ) -> MedicationReviewResult:

        system_prompt, user_prompt = (
            self.build_medication_review_prompt(
                documents
            )
        )

        response = await self.client.responses.parse(
            model=settings.openai_model,

            input=[
                {
                    "role":"system",
                    "content":system_prompt
                },
                {
                    "role":"user",
                    "content":user_prompt
                }
            ],

            text_format=MedicationReviewResult,

            temperature=0
        )
        return response.output_parsed