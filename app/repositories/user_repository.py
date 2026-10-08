from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Case-insensitive, so accounts created before emails were normalized still match."""
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.strip().lower()).order_by(User.created_at).limit(1)
        )
        return result.scalar_one_or_none()
