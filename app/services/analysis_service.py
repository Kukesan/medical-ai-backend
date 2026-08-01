import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisResult
from app.models.enums import ProcessingStatus, RiskLevel
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService
from app.services.lab_trend_service import LabTrendService
from app.services.medication_analysis_service import MedicationAnalysisService
from app.services.ocr_service import OCRService
from app.services.timeline_service import TimelineService


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.analysis_repo = AnalysisRepository(session)

        self.ocr = OCRService()
        self.extractor = ExtractionService()
        self.timeline = TimelineService(session)
        self.medication = MedicationAnalysisService(session)
        self.lab = LabTrendService(session)
        self.embedding = EmbeddingService(session)

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

            await self.embedding.index_document(user_id, document.id)

        med_result = await self.medication.analyze(user_id)
        high_risk = len(med_result.get("drug_interactions", [])) > 0
        risk_level = RiskLevel.HIGH if high_risk else RiskLevel.LOW

        analysis_row = AnalysisResult(
            user_id=user_id,
            result_type="medication_cross_check",
            risk_level=risk_level,
            explanation=(
                "Cross-document analysis completed. This does not diagnose conditions; "
                "please consult a healthcare professional for decisions."
            ),
            evidence=med_result.get("drug_interactions", []),
            confidence=0.7 if high_risk else 0.6,
        )
        await self.analysis_repo.create(analysis_row)

        await self.timeline.build_for_user(user_id)
        _ = await self.lab.trends(user_id)

        await self.session.commit()
