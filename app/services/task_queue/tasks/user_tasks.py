from faker import Faker
from loguru import logger
from pwdlib import PasswordHash
from sqlalchemy import insert

from app.core.db import session_factory
from app.models import User
from app.schemas import UserCreate
from app.services.task_queue import celery_app

password_hash = PasswordHash.recommended()


@celery_app.task(name="seed_fake_users", bind=True)
def seed_fake_users_task(self, count: int = 100) -> int:
    """
    Celery task to seed fake users into the database.

    Args:
        self: The task instance (automatically passed by Celery).
        count (int): Number of fake users to create. Default is 100.

    Returns:
        int: The number of users created.
    """
    logger.info(f"Starting seed task {self.request.id} to create {count} users")

    faker = Faker()
    hashed_password = password_hash.hash("TestPassword123")
    all_users: list[UserCreate] = []

    for _ in range(count):
        user_new = UserCreate(
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            username=faker.user_name(),
            email=faker.email(),
            hashed_password=hashed_password,
        )
        all_users.append(user_new)
        logger.info(f"appended user: {user_new.username}")

    with session_factory() as session:
        values = [schema.model_dump(exclude_none=True) for schema in all_users]
        stmt = insert(User).values(values)
        session.execute(stmt)
        session.commit()
        logger.debug(f"Generated {count} user objects")

    return count
