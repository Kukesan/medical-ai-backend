import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.core.security import verify_password
from app.models.analysis_result import AnalysisResult
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.embedding import Embedding
from app.models.medical_document import MedicalDocument
from app.models.medical_record import MedicalRecord
from app.models.patient_timeline import PatientTimeline
from app.models.record_intake_session import RecordIntakeSession
from app.models.user import User
from app.models.vitals import Vitals
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileCreateRequest, UserProfileResponse, UserProfileUpdateRequest
from app.services.s3_service import S3Service
from app.services.storage_service import LocalStorageService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_profile(self, user: User) -> UserProfileResponse:
        return UserProfileResponse.model_validate(user)

    async def create_profile(self, user: User, profile_data: UserProfileCreateRequest) -> UserProfileResponse:
        user.date_of_birth = profile_data.date_of_birth
        user.bio = profile_data.bio
        user.notes = profile_data.notes
        await self.session.commit()
        await self.session.refresh(user)
        return UserProfileResponse.model_validate(user)

    async def update_profile(self, user: User, profile_data: UserProfileUpdateRequest) -> UserProfileResponse:
        updates = profile_data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(user, field, value)
        await self.session.commit()
        await self.session.refresh(user)
        return UserProfileResponse.model_validate(user)

    async def delete_account(self, user: User, password: str) -> None:
        """Permanently delete the user and all of their health data, including stored files."""
        if not verify_password(password, user.hashed_password):
            # 403, not 401: the session is valid, so the client must not treat this as an expired token.
            raise ForbiddenException("Password is incorrect")

        user_id = user.id
        file_paths = list(
            (await self.session.execute(select(MedicalDocument.file_path).where(MedicalDocument.user_id == user_id)))
            .scalars()
            .all()
        )

        # Bulk deletes in dependency order: the self-reference and cross-table FKs have no
        # ON DELETE CASCADE, so ORM cascades alone could hit FK violations.
        user_sessions = select(ChatSession.id).where(ChatSession.user_id == user_id)
        await self.session.execute(delete(Embedding).where(Embedding.user_id == user_id))
        await self.session.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(user_sessions)))
        await self.session.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
        await self.session.execute(delete(RecordIntakeSession).where(RecordIntakeSession.user_id == user_id))
        await self.session.execute(
            update(MedicalRecord).where(MedicalRecord.user_id == user_id).values(conflict_with_record_id=None)
        )
        await self.session.execute(delete(MedicalRecord).where(MedicalRecord.user_id == user_id))
        await self.session.execute(delete(PatientTimeline).where(PatientTimeline.user_id == user_id))
        await self.session.execute(delete(AnalysisResult).where(AnalysisResult.user_id == user_id))
        await self.session.execute(delete(Vitals).where(Vitals.user_id == user_id))
        await self.session.execute(delete(MedicalDocument).where(MedicalDocument.user_id == user_id))
        await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.commit()

        # Files go after the commit so a storage hiccup can't leave a half-deleted account.
        await self._delete_files(file_paths)

    @staticmethod
    async def _delete_files(file_paths: list[str]) -> None:
        local_storage = LocalStorageService()
        s3: S3Service | None = None
        for file_path in file_paths:
            try:
                if S3Service.is_s3_key(file_path):
                    s3 = s3 or S3Service()
                    await s3.delete_object(file_path)
                else:
                    local_storage.delete(file_path)
            except Exception:
                logger.exception("Failed to delete stored file %s during account deletion", file_path)
