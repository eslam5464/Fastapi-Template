from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repos import BaseRepository
from app.schemas import UserCreate, UserUpdate


class UserRepo(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        """User repository for database operations"""
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> User | None:
        """
        Get a user by username

        Args:
            username (str): The username of the user.

        Returns:
            User | None: The user object if found, else None.
        """
        query = select(self.model).where(self.model.username == username)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Get a user by email

        Args:
            email (str): The email of the user.

        Returns:
            User | None: The user object if found, else None.
        """
        query = select(self.model).where(self.model.email == email)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()
