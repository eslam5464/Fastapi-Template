import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from tests.sample_model import (
    SampleRecord,
    SampleRecordRepo,
    SampleRecordUpdate,
    sample_record_data,
)


@pytest.mark.anyio
class TestBaseRepositoryValidation:
    """Test column validation in BaseRepository."""

    async def test_validate_column_exists_valid(self, db_session: AsyncSession):
        """Test that validation passes for valid column."""
        repo = SampleRecordRepo(db_session)
        # Should not raise any exception
        repo._validate_column_exists("id")
        repo._validate_column_exists("code")
        repo._validate_column_exists("name")

    async def test_validate_column_exists_invalid(self, db_session: AsyncSession):
        """Test that validation fails for invalid column."""
        repo = SampleRecordRepo(db_session)

        with pytest.raises(ValueError, match="Column 'nonexistent_column' does not exist"):
            repo._validate_column_exists("nonexistent_column")

    async def test_get_by_id_invalid_column(self, db_session: AsyncSession, sample_record: SampleRecord):
        """Test get_by_id with invalid column name raises ValueError."""
        repo = SampleRecordRepo(db_session)

        with pytest.raises(ValueError, match="Column 'invalid_column' does not exist"):
            await repo.get_by_id(sample_record.id, id_column_name="invalid_column")


@pytest.mark.anyio
class TestBaseRepositoryCreate:
    """Test creation operations in BaseRepository."""

    async def test_create_one_exclude_none_true(self, db_session: AsyncSession, faker: Faker):
        """Test creating single record with exclude_none=True (default)."""
        repo = SampleRecordRepo(db_session)
        record_data = sample_record_data(faker, note="")

        created_record = await repo.create_one(record_data, exclude_none=True)

        assert created_record.code == record_data.code
        assert created_record.name == record_data.name
        assert created_record.label == record_data.label
        assert created_record.id is not None

    async def test_create_one_exclude_none_false(self, db_session: AsyncSession, faker: Faker):
        """Test creating single record with exclude_none=False."""
        repo = SampleRecordRepo(db_session)
        record_data = sample_record_data(faker, note="")

        created_record = await repo.create_one(record_data, exclude_none=False)

        assert created_record.code == record_data.code
        assert created_record.note == ""  # Empty string, not None

    async def test_create_bulk_empty_list(self, db_session: AsyncSession):
        """Test that create_bulk with empty list returns empty list."""
        repo = SampleRecordRepo(db_session)

        result = await repo.create_bulk([])

        assert result == []

    async def test_create_bulk_success(self, db_session: AsyncSession, faker: Faker):
        """Test bulk creation of multiple records."""
        repo = SampleRecordRepo(db_session)
        records_data = [sample_record_data(faker) for _ in range(3)]

        created_records = await repo.create_bulk(records_data)

        assert len(created_records) == 3
        for i, created_record in enumerate(created_records):
            assert created_record.code == records_data[i].code
            assert created_record.name == records_data[i].name
            assert created_record.id is not None

    async def test_create_bulk_exclude_none_false(self, db_session: AsyncSession, faker: Faker):
        """Test bulk creation with exclude_none=False."""
        repo = SampleRecordRepo(db_session)
        records_data = [sample_record_data(faker, note="") for _ in range(2)]

        created_records = await repo.create_bulk(records_data, exclude_none=False)

        assert len(created_records) == 2
        assert all(record.note == "" for record in created_records)


@pytest.mark.anyio
class TestBaseRepositoryRead:
    """Test read operations in BaseRepository."""

    async def test_get_by_id_custom_column(self, db_session: AsyncSession, sample_record: SampleRecord):
        """Test get_by_id with custom column name."""
        repo = SampleRecordRepo(db_session)

        # Get by code column
        result = await repo.get_by_id(sample_record.code, id_column_name="code")

        assert result is not None
        assert result.id == sample_record.id
        assert result.code == sample_record.code

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test get_by_id returns None when record not found."""
        repo = SampleRecordRepo(db_session)
        non_existent_id = 999999999

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_multi_by_ids_pagination(self, db_session: AsyncSession, faker: Faker):
        """Test get_multi_by_ids with pagination."""
        repo = SampleRecordRepo(db_session)

        # Create 5 records
        records_data = [sample_record_data(faker) for _ in range(5)]
        created_records = await repo.create_bulk(records_data)
        record_ids = [record.id for record in created_records]

        # Get first 2 records
        result = await repo.get_multi_by_ids(skip=0, limit=2, obj_ids=record_ids)
        assert len(result) == 2

        # Get next 2 records
        result = await repo.get_multi_by_ids(skip=2, limit=2, obj_ids=record_ids)
        assert len(result) == 2

        # Get last record
        result = await repo.get_multi_by_ids(skip=4, limit=2, obj_ids=record_ids)
        assert len(result) == 1

    async def test_get_multi_by_ids_empty_list(self, db_session: AsyncSession):
        """Test get_multi_by_ids with empty ID list."""
        repo = SampleRecordRepo(db_session)

        result = await repo.get_multi_by_ids(obj_ids=[])

        assert len(result) == 0

    async def test_get_multi_by_ids_custom_column(self, db_session: AsyncSession, faker: Faker):
        """Test get_multi_by_ids with custom column name."""
        repo = SampleRecordRepo(db_session)

        # Create records
        records_data = [sample_record_data(faker) for _ in range(3)]
        created_records = await repo.create_bulk(records_data)
        names = [record.name for record in created_records]

        # Get by names
        result = await repo.get_multi_by_ids(id_column_name="name", obj_ids=names)

        assert len(result) == 3
        assert all(record.name in names for record in result)


@pytest.mark.anyio
class TestBaseRepositoryUpdate:
    """Test update operations in BaseRepository."""

    async def test_update_by_id_not_found(self, db_session: AsyncSession, faker: Faker):
        """Test update_by_id returns None when record not found."""
        repo = SampleRecordRepo(db_session)
        non_existent_id = 999999999
        update_data = SampleRecordUpdate(label=faker.first_name())

        result = await repo.update_by_id(non_existent_id, update_data)

        assert result is None

    async def test_update_by_id_custom_column(
        self, db_session: AsyncSession, sample_record: SampleRecord, faker: Faker
    ):
        """Test update_by_id with custom column name."""
        repo = SampleRecordRepo(db_session)
        new_first_name = faker.first_name()
        update_data = SampleRecordUpdate(label=new_first_name)

        # Update using code as identifier
        result = await repo.update_by_id(sample_record.code, update_data, id_column_name="code")

        assert result is not None
        assert result.label == new_first_name
        assert result.code == sample_record.code

    async def test_update_by_id_exclude_none(self, db_session: AsyncSession, sample_record: SampleRecord, faker: Faker):
        """Test update_by_id with exclude_none=True (default behavior)."""
        repo = SampleRecordRepo(db_session)
        new_first_name = faker.first_name()
        update_data = SampleRecordUpdate(label=new_first_name, code=sample_record.code)

        # Update with exclude_none=True (default)
        result = await repo.update_by_id(sample_record.id, update_data, exclude_none=True)

        assert result is not None
        assert result.label == new_first_name
        # note should remain unchanged
        assert result.note == sample_record.note

    async def test_update_bulk_empty(self, db_session: AsyncSession):
        """Test update_bulk with empty list returns empty list."""
        repo = SampleRecordRepo(db_session)

        result = await repo.update_bulk([])

        assert result == []

    async def test_update_bulk_partial(self, db_session: AsyncSession, faker: Faker):
        """Test update_bulk with partial updates (some IDs don't exist)."""
        repo = SampleRecordRepo(db_session)

        # Create 2 records
        records_data = [sample_record_data(faker) for _ in range(2)]
        created_records = await repo.create_bulk(records_data)

        # Prepare updates: 2 existing + 1 non-existent
        non_existent_id = 999999999
        updates = [
            (created_records[0].id, SampleRecordUpdate(label="Updated1")),
            (non_existent_id, SampleRecordUpdate(label="NonExistent")),
            (created_records[1].id, SampleRecordUpdate(label="Updated2")),
        ]

        result = await repo.update_bulk(updates)

        # Should only update the 2 existing records
        assert len(result) == 2
        assert result[0].label == "Updated1"
        assert result[1].label == "Updated2"

    async def test_update_bulk_success(self, db_session: AsyncSession, faker: Faker):
        """Test successful bulk update of multiple records."""
        repo = SampleRecordRepo(db_session)

        # Create 3 records
        records_data = [sample_record_data(faker) for _ in range(3)]
        created_records = await repo.create_bulk(records_data)

        # Update all records
        updates = [(record.id, SampleRecordUpdate(label=f"Updated{i}")) for i, record in enumerate(created_records)]

        result = await repo.update_bulk(updates)

        assert len(result) == 3
        for i, updated_record in enumerate(result):
            assert updated_record.label == f"Updated{i}"

    async def test_update_bulk_custom_column(self, db_session: AsyncSession, faker: Faker):
        """Test update_bulk with custom column name."""
        repo = SampleRecordRepo(db_session)

        # Create records
        records_data = [sample_record_data(faker) for _ in range(2)]
        created_records = await repo.create_bulk(records_data)

        # Update using name as identifier
        updates = [(record.name, SampleRecordUpdate(label=f"NewName{i}")) for i, record in enumerate(created_records)]

        result = await repo.update_bulk(updates, id_column_name="name")

        assert len(result) == 2
        for i, updated_record in enumerate(result):
            assert updated_record.label == f"NewName{i}"


@pytest.mark.anyio
class TestBaseRepositoryDelete:
    """Test delete operations in BaseRepository."""

    async def test_delete_by_id_not_found(self, db_session: AsyncSession):
        """Test delete_by_id returns False when record not found."""
        repo = SampleRecordRepo(db_session)
        non_existent_id = 999999999

        result = await repo.delete_by_id(non_existent_id)

        assert result is False

    async def test_delete_by_id_success(self, db_session: AsyncSession, sample_record: SampleRecord):
        """Test successful deletion by ID."""
        repo = SampleRecordRepo(db_session)
        record_id = sample_record.id

        result = await repo.delete_by_id(record_id)

        assert result is True

        # Verify record is deleted
        deleted_record = await repo.get_by_id(record_id)
        assert deleted_record is None

    async def test_delete_by_id_custom_column(self, db_session: AsyncSession, sample_record: SampleRecord):
        """Test delete_by_id with custom column name."""
        repo = SampleRecordRepo(db_session)
        record_code = sample_record.code

        result = await repo.delete_by_id(record_code, id_column_name="code")

        assert result is True

        # Verify record is deleted
        deleted_record = await repo.get_by_id(record_code, id_column_name="code")
        assert deleted_record is None

    async def test_delete_by_ids_empty(self, db_session: AsyncSession):
        """Test delete_by_ids with empty list returns 0."""
        repo = SampleRecordRepo(db_session)

        result = await repo.delete_by_ids([])

        assert result == 0

    async def test_delete_by_ids_partial(self, db_session: AsyncSession, faker: Faker):
        """Test delete_by_ids with partial deletions (some IDs don't exist)."""
        repo = SampleRecordRepo(db_session)

        # Create 2 records
        records_data = [sample_record_data(faker) for _ in range(2)]
        created_records = await repo.create_bulk(records_data)

        # Try to delete 2 existing + 1 non-existent
        non_existent_id = 999999999
        ids_to_delete = [created_records[0].id, non_existent_id, created_records[1].id]

        result = await repo.delete_by_ids(ids_to_delete)

        # Should delete only 2 existing records
        assert result == 2

    async def test_delete_by_ids_success(self, db_session: AsyncSession, faker: Faker):
        """Test successful bulk deletion."""
        repo = SampleRecordRepo(db_session)

        # Create 3 records
        records_data = [sample_record_data(faker) for _ in range(3)]
        created_records = await repo.create_bulk(records_data)
        record_ids = [record.id for record in created_records]

        result = await repo.delete_by_ids(record_ids)

        assert result == 3

        # Verify all records are deleted
        remaining_records = await repo.get_multi_by_ids(obj_ids=record_ids)
        assert len(remaining_records) == 0

    async def test_delete_by_ids_custom_column(self, db_session: AsyncSession, faker: Faker):
        """Test delete_by_ids with custom column name."""
        repo = SampleRecordRepo(db_session)

        # Create records
        records_data = [sample_record_data(faker) for _ in range(2)]
        created_records = await repo.create_bulk(records_data)
        names = [record.name for record in created_records]

        result = await repo.delete_by_ids(names, id_column_name="name")

        assert result == 2


@pytest.mark.anyio
class TestBaseRepositoryCustomQuery:
    """Test custom query execution in BaseRepository."""

    async def test_custom_query_select(self, db_session: AsyncSession, faker: Faker):
        """Test custom_query with SELECT statement."""
        repo = SampleRecordRepo(db_session)

        # Create a record
        record_data = sample_record_data(faker)
        created_record = await repo.create_one(record_data)

        # Execute custom query with schema prefix
        schema = settings.postgres_db_schema
        query = f'SELECT * FROM {schema}.{SampleRecord.__tablename__} WHERE "id" = {created_record.id}'
        result = await repo.custom_query(query)

        fetched_row = result.fetchone()
        assert fetched_row is not None

    async def test_custom_query_count(self, db_session: AsyncSession, faker: Faker):
        """Test custom_query with COUNT statement."""
        repo = SampleRecordRepo(db_session)

        # Create multiple records
        records_data = [sample_record_data(faker) for _ in range(5)]
        await repo.create_bulk(records_data)

        # Count records with schema prefix
        schema = settings.postgres_db_schema
        query = f"SELECT COUNT(*) FROM {schema}.{SampleRecord.__tablename__}"
        result = await repo.custom_query(query)

        count = result.scalar()
        assert count is not None
        assert count >= 5
