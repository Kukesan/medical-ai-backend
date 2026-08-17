from fastapi import APIRouter

from app.api.v1.routes import (
    analysis,
    auth,
    chat,
    consultant,
    dashboard,
    documents,
    document_s3,
    medical_records,
    record_intake,
    record_types,
    user,
    timeline,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(document_s3.router, tags=["documents"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(user.router, tags=["user"])
api_router.include_router(consultant.router, tags=["consultant"])
api_router.include_router(timeline.router, tags=["timeline"])
api_router.include_router(medical_records.router, tags=["medical-records"])
api_router.include_router(record_types.router, tags=["record-types"])
api_router.include_router(record_intake.router, tags=["record-intake"])
