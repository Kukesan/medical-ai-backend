from fastapi import APIRouter

from app.api.v1.routes import analysis, auth, chat, dashboard, documents, allergy

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(allergy.router, tags=["allergy"])
