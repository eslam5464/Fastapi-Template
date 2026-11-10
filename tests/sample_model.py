"""A model, its schemas and its repository that exist only for the tests.

The generic layers (Base, BaseRepository, BaseSchema) are tested through
SampleRecord, so those tests do not depend on any domain model of the project.

tests/conftest.py imports this module, which registers the table on
Base.metadata. The test database is built with `create_all`, so the table
exists only there: Alembic imports `app.models` and never sees it.
"""

from faker import Faker
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.repos.base import BaseRepository
from app.schemas.base import BaseSchema


class SampleRecord(Base):
    """A table with two unique columns and three plain ones."""

    code: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    payload: Mapped[str] = mapped_column(String(1000), nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str] = mapped_column(String(50), nullable=False)


class SampleRecordCreate(BaseSchema):
    code: str
    name: str
    payload: str
    label: str
    note: str


class SampleRecordUpdate(BaseSchema):
    code: str | None = None
    name: str | None = None
    label: str | None = None
    note: str | None = None


class SampleRecordRepo(BaseRepository[SampleRecord, SampleRecordCreate, SampleRecordUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, SampleRecord)


def sample_record_data(faker: Faker, **overrides: str) -> SampleRecordCreate:
    """Valid, unique data for one SampleRecord; `overrides` replace single fields."""
    values = {
        "code": faker.unique.uuid4(),
        "name": faker.unique.user_name(),
        "payload": faker.sentence(),
        "label": faker.first_name(),
        "note": faker.last_name(),
    }
    values.update(overrides)
    return SampleRecordCreate(**values)
