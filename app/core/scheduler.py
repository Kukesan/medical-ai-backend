import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.database.session import SessionLocal
from app.services.document_service import DocumentService
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_pending_ocr_extraction() -> None:
    async with SessionLocal() as session:
        service = DocumentService(session, LocalStorageService())
        try:
            succeeded, failed = await service.extract_pending_ocr_documents()
        except Exception:
            logger.exception("Scheduled OCR extraction run failed")
            return

    if succeeded or failed:
        logger.info(
            "Scheduled OCR extraction run complete: %d succeeded, %d failed",
            len(succeeded),
            len(failed),
        )


def start_scheduler() -> None:
    if not settings.ocr_extraction_scheduler_enabled:
        logger.info("OCR extraction scheduler is disabled")
        return

    scheduler.add_job(
        run_pending_ocr_extraction,
        trigger="interval",
        minutes=settings.ocr_extraction_scheduler_interval_minutes,
        id="extract_pending_ocr_documents",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "OCR extraction scheduler started (interval=%d minutes)",
        settings.ocr_extraction_scheduler_interval_minutes,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
