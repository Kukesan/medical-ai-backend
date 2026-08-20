import json
import uuid
from pathlib import Path
from app.ai.interaction_checker.medication_interaction_service import MedicationInteractionService

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult
from app.models.enums import AlertCategory, ProcessingStatus, RiskLevel
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.services.extraction_service import ExtractionService
from app.services.lab_trend_service import LabTrendService
from app.services.medication_analysis_service import MedicationAnalysisService
from app.services.ocr_service import OCRService
from app.schemas.medication_analyze import MedicalAnalysisListResponse, MedicalAnalysisReponse, MedicalAnalysisReponse, MedicalDocumentInput, MedicationAlert, MedicationReviewResult

class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.analysis_repo = AnalysisRepository(session)

        self.ocr = OCRService()
        self.extractor = ExtractionService()
        self.medication = MedicationAnalysisService(session)
        self.lab = LabTrendService(session)

    @staticmethod
    def _coerce_alert_category(value: str | None) -> AlertCategory:
        category_map = {
            "drug_interaction": AlertCategory.DRUG_INTERACTION,
            "duplicate_medication": AlertCategory.DUPLICATE_MEDICATION,
            "allergy_conflict": AlertCategory.ALLERGY_CONFLICT,
            "dosage_conflict": AlertCategory.DOSAGE_CONFLICT,
            "conflicting_dosage": AlertCategory.DOSAGE_CONFLICT,
            "medication_change": AlertCategory.MEDICATION_CHANGE,
            "expired_prescription": AlertCategory.MEDICATION_CHANGE,
            "lab_abnormality": AlertCategory.LAB_ABNORMALITY,
        }
        return category_map.get((value or "").lower(), AlertCategory.MEDICATION_CHANGE)

    @classmethod
    def _build_result_from_local_alert(cls, user_id: uuid.UUID, alert: dict) -> AnalysisResult:
        assessment = alert.get("assessment") or {}
        raw_risk = assessment.get("risk_level")
        if isinstance(raw_risk, RiskLevel):
            risk_level = raw_risk
        elif isinstance(raw_risk, str) and raw_risk.lower() in {"low", "medium", "high"}:
            risk_level = RiskLevel(raw_risk.lower())
        else:
            risk_level = RiskLevel.LOW

        evidence: list[dict] = []
        for item in assessment.get("evidence") or []:
            evidence.append(
                {
                    "document_id": item.get("source_document_id"),
                    "snippet": item.get("snippet", ""),
                }
            )

        description = alert.get("details", "")
        clinical_reason = assessment.get("explanation", description)

        return AnalysisResult(
            user_id=user_id,
            category=cls._coerce_alert_category(alert.get("category")),
            risk_level=risk_level,
            title=description or "Medication alert",
            description=description,
            clinical_reason=clinical_reason,
            timeline=[],
            evidence=evidence,
            recommendation="Discuss with healthcare professional",
            confidence=float(assessment.get("confidence", 0.0) or 0.0),
        )

    @classmethod
    def _build_result_from_ai_alert(cls, user_id: uuid.UUID, alert: MedicationAlert) -> AnalysisResult:
        return AnalysisResult(
            user_id=user_id,
            category=cls._coerce_alert_category(alert.category.value),
            risk_level=alert.risk_level,
            title=alert.title,
            description=alert.description,
            clinical_reason=alert.clinical_reason,
            timeline=[item.model_dump(mode="json", exclude_none=True) for item in alert.timeline],
            evidence=[item.model_dump(mode="json",exclude_none=True) for item in alert.evidence],
            recommendation=alert.recommendation,
            confidence=alert.confidence,
        )

    async def run_for_documents(self, user_id: uuid.UUID, document_ids: list[uuid.UUID]) -> None:
        for document_id in document_ids:
            document = await self.doc_repo.get_by_user_and_id(user_id, document_id)
            if not document:
                continue

            ocr_result = await self.ocr.process(Path(document.file_path))
            document.ocr_text = ocr_result.get("text", "")
            document.ocr_metadata = ocr_result.get("metadata", {})
            document.processing_status = ProcessingStatus.OCR_COMPLETED

            extracted = await self.extractor.run(document.ocr_text)
            document.extraction_result = extracted
            document.processing_status = ProcessingStatus.EXTRACTED

        med_result = await self.medication.analyze(user_id)
        grouped_alerts = [
            "duplicate_medications",
            "drug_interactions",
            "conflicting_dosages",
            "expired_prescriptions",
            "medication_changes",
            "allergy_alerts",
        ]
        for key in grouped_alerts:
            for alert in med_result.get(key, []):
                await self.analysis_repo.create(self._build_result_from_local_alert(user_id, alert))

        _ = await self.lab.trends(user_id)

        await self.session.commit()

    async def get_analysis_results(self, user_id: uuid.UUID) -> list[MedicalAnalysisListResponse]:
        results = await self.analysis_repo.list_by_user(user_id)
        results = sorted(
            results,
            key=lambda result: (result.created_at is not None, result.created_at),
            reverse=True,
        )
        
        return [MedicalAnalysisListResponse(
            id=result.id,
            user_id=result.user_id,
            category=result.category,
            risk_level=result.risk_level,
            title=result.title,
            description=result.description,
            confidence=result.confidence,
            created_at=result.created_at,
        ) for result in results]

    async def get_analysis_result_by_id(self, user_id: uuid.UUID, result_id: uuid.UUID) -> MedicalAnalysisReponse | None:
        result = await self.analysis_repo.get_by_user_and_id(user_id, result_id)
        if not result:
            return None
        return MedicalAnalysisReponse(
            id=result.id,
            user_id=result.user_id,
            category=result.category,
            risk_level=result.risk_level,
            title=result.title,
            description=result.description,
            clinical_reason=result.clinical_reason,
            confidence=result.confidence,
            timeline=result.timeline,
            evidence=result.evidence,
            recommendation=result.recommendation,
            created_at=result.created_at,
        )

    async def analyze_medication_interactions(self, user_id: uuid.UUID) -> dict:
        medication_interaction_service = MedicationInteractionService()
        documents = await self.doc_repo.list_by_user(user_id)
        if documents:
            document_inputs: list[MedicalDocumentInput] = [
                MedicalDocumentInput(
                    document_id=document.id,
                    document_date=document.created_at.isoformat() if document.created_at else None,
                    ocr_text=document.ocr_text or "",
                )
                for document in documents
            ]
            medication_review_result: MedicationReviewResult = await medication_interaction_service.review_medication_history(document_inputs)
            if medication_review_result:
                for alert in medication_review_result.alerts:
                    await self.analysis_repo.create(self._build_result_from_ai_alert(user_id, alert))
                await self.session.commit()
            return medication_review_result.model_dump()
        return {}
      