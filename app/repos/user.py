from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_password_hash, verify_password
from app.repos import BaseRepository
from app.models.user import User
from app.schemas import UserCreate, UserUpdate


class UserRepo(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        """User repository for CRUD operations."""
        super().__init__(session, User)

    async def create_user(
        self,
        user_in: UserCreate,
    ) -> User:
        """Create a new user with hashed password"""
        user_in.password = get_password_hash(user_in.password)
        stmt = (
            insert(self.model)
            .values(**user_in.model_dump(exclude_none=True))
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by username"""
        query = select(self.model).where(self.model.username == username)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email"""
        query = select(self.model).where(self.model.email == email)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    # async def authenticate_by_email(self, email: str, password: str) -> User | None:
    #     """Authenticate a user"""
    #     user = await self.get_by_email(email)

    #     if not user:
    #         return None

    #     if not verify_password(password, user.hashed_password):
    #         return None

    #     return user

    # async def authenticate_by_username(
    #     self, username: str, password: str
    # ) -> User | None:
    #     """Authenticate a user by username"""
    #     user = await self.get_by_username(username)

    #     if not user:
    #         return None

    #     if not verify_password(password, user.hashed_password):
    #         return None

    #     return user
