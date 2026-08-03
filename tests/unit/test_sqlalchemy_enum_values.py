from app.models.analysis_result import AnalysisResult
from app.models.chat_message import ChatMessage
from app.models.enums import DocumentType, MessageRole, ProcessingStatus, RiskLevel
from app.models.medical_document import MedicalDocument


def test_sqlalchemy_enums_use_enum_values() -> None:
    document_type_values = MedicalDocument.__table__.c.document_type.type.enums
    processing_status_values = MedicalDocument.__table__.c.processing_status.type.enums
    risk_level_values = AnalysisResult.__table__.c.risk_level.type.enums
    role_values = ChatMessage.__table__.c.role.type.enums

    assert document_type_values == [item.value for item in DocumentType]
    assert processing_status_values == [item.value for item in ProcessingStatus]
    assert risk_level_values == [item.value for item in RiskLevel]
    assert role_values == [item.value for item in MessageRole]
