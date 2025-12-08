import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app import repos
from app.models import User
from app.schemas import UserCreate, UserUpdate


@pytest.mark.anyio
class TestBaseRepositoryValidation:
    """Test column validation in BaseRepository."""

    async def test_validate_column_exists_valid(self, db_session: AsyncSession):
        """Test that validation passes for valid column."""
        repo = repos.UserRepo(db_session)
        # Should not raise any exception
        repo._validate_column_exists("id")
        repo._validate_column_exists("email")
        repo._validate_column_exists("username")

    async def test_validate_column_exists_invalid(self, db_session: AsyncSession):
        """Test that validation fails for invalid column."""
        repo = repos.UserRepo(db_session)

        with pytest.raises(ValueError, match="Column 'nonexistent_column' does not exist"):
            repo._validate_column_exists("nonexistent_column")

    async def test_get_by_id_invalid_column(self, db_session: AsyncSession, user: User):
        """Test get_by_id with invalid column name raises ValueError."""
        repo = repos.UserRepo(db_session)

        with pytest.raises(ValueError, match="Column 'invalid_column' does not exist"):
            await repo.get_by_id(user.id, id_column_name="invalid_column")


@pytest.mark.anyio
class TestBaseRepositoryCreate:
    """Test creation operations in BaseRepository."""

    async def test_create_one_exclude_none_true(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test creating single record with exclude_none=True (default)."""
        repo = repos.UserRepo(db_session)
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name="",  # Empty string instead of None
        )

        created_user = await repo.create_one(user_data, exclude_none=True)

        assert created_user.email == user_data.email
        assert created_user.username == user_data.username
        assert created_user.first_name == user_data.first_name
        assert created_user.id is not None

    async def test_create_one_exclude_none_false(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test creating single record with exclude_none=False."""
        repo = repos.UserRepo(db_session)
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name="",  # Empty string instead of None
        )

        created_user = await repo.create_one(user_data, exclude_none=False)

        assert created_user.email == user_data.email
        assert created_user.last_name == ""  # Empty string, not None

    async def test_create_bulk_empty_list(self, db_session: AsyncSession):
        """Test that create_bulk with empty list returns empty list."""
        repo = repos.UserRepo(db_session)

        result = await repo.create_bulk([])

        assert result == []

    async def test_create_bulk_success(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test bulk creation of multiple users."""
        repo = repos.UserRepo(db_session)
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(3)
        ]

        created_users = await repo.create_bulk(users_data)

        assert len(created_users) == 3
        for i, created_user in enumerate(created_users):
            assert created_user.email == users_data[i].email
            assert created_user.username == users_data[i].username
            assert created_user.id is not None

    async def test_create_bulk_exclude_none_false(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test bulk creation with exclude_none=False."""
        repo = repos.UserRepo(db_session)
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name="",  # Empty string instead of None
            )
            for _ in range(2)
        ]

        created_users = await repo.create_bulk(users_data, exclude_none=False)

        assert len(created_users) == 2
        assert all(user.last_name == "" for user in created_users)


@pytest.mark.anyio
class TestBaseRepositoryRead:
    """Test read operations in BaseRepository."""

    async def test_get_by_id_custom_column(self, db_session: AsyncSession, user: User):
        """Test get_by_id with custom column name."""
        repo = repos.UserRepo(db_session)

        # Get by email column
        result = await repo.get_by_id(user.email, id_column_name="email")

        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test get_by_id returns None when record not found."""
        repo = repos.UserRepo(db_session)
        non_existent_id = 999999999

        result = await repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_multi_by_ids_pagination(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test get_multi_by_ids with pagination."""
        repo = repos.UserRepo(db_session)

        # Create 5 users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(5)
        ]
        created_users = await repo.create_bulk(users_data)
        user_ids = [user.id for user in created_users]

        # Get first 2 users
        result = await repo.get_multi_by_ids(skip=0, limit=2, obj_ids=user_ids)
        assert len(result) == 2

        # Get next 2 users
        result = await repo.get_multi_by_ids(skip=2, limit=2, obj_ids=user_ids)
        assert len(result) == 2

        # Get last user
        result = await repo.get_multi_by_ids(skip=4, limit=2, obj_ids=user_ids)
        assert len(result) == 1

    async def test_get_multi_by_ids_empty_list(self, db_session: AsyncSession):
        """Test get_multi_by_ids with empty ID list."""
        repo = repos.UserRepo(db_session)

        result = await repo.get_multi_by_ids(obj_ids=[])

        assert len(result) == 0

    async def test_get_multi_by_ids_custom_column(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test get_multi_by_ids with custom column name."""
        repo = repos.UserRepo(db_session)

        # Create users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(3)
        ]
        created_users = await repo.create_bulk(users_data)
        usernames = [user.username for user in created_users]

        # Get by usernames
        result = await repo.get_multi_by_ids(id_column_name="username", obj_ids=usernames)

        assert len(result) == 3
        assert all(user.username in usernames for user in result)


@pytest.mark.anyio
class TestBaseRepositoryUpdate:
    """Test update operations in BaseRepository."""

    async def test_update_by_id_not_found(self, db_session: AsyncSession, faker: Faker):
        """Test update_by_id returns None when record not found."""
        repo = repos.UserRepo(db_session)
        non_existent_id = 999999999
        update_data = UserUpdate(first_name=faker.first_name())

        result = await repo.update_by_id(non_existent_id, update_data)

        assert result is None

    async def test_update_by_id_custom_column(
        self, db_session: AsyncSession, user: User, faker: Faker
    ):
        """Test update_by_id with custom column name."""
        repo = repos.UserRepo(db_session)
        new_first_name = faker.first_name()
        update_data = UserUpdate(first_name=new_first_name)

        # Update using email as identifier
        result = await repo.update_by_id(user.email, update_data, id_column_name="email")

        assert result is not None
        assert result.first_name == new_first_name
        assert result.email == user.email

    async def test_update_by_id_exclude_none(
        self, db_session: AsyncSession, user: User, faker: Faker
    ):
        """Test update_by_id with exclude_none=True (default behavior)."""
        repo = repos.UserRepo(db_session)
        new_first_name = faker.first_name()
        update_data = UserUpdate(first_name=new_first_name, email=user.email)

        # Update with exclude_none=True (default)
        result = await repo.update_by_id(user.id, update_data, exclude_none=True)

        assert result is not None
        assert result.first_name == new_first_name
        # last_name should remain unchanged
        assert result.last_name == user.last_name

    async def test_update_bulk_empty(self, db_session: AsyncSession):
        """Test update_bulk with empty list returns empty list."""
        repo = repos.UserRepo(db_session)

        result = await repo.update_bulk([])

        assert result == []

    async def test_update_bulk_partial(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test update_bulk with partial updates (some IDs don't exist)."""
        repo = repos.UserRepo(db_session)

        # Create 2 users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(2)
        ]
        created_users = await repo.create_bulk(users_data)

        # Prepare updates: 2 existing + 1 non-existent
        non_existent_id = 999999999
        updates = [
            (created_users[0].id, UserUpdate(first_name="Updated1")),
            (non_existent_id, UserUpdate(first_name="NonExistent")),
            (created_users[1].id, UserUpdate(first_name="Updated2")),
        ]

        result = await repo.update_bulk(updates)

        # Should only update the 2 existing users
        assert len(result) == 2
        assert result[0].first_name == "Updated1"
        assert result[1].first_name == "Updated2"

    async def test_update_bulk_success(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test successful bulk update of multiple records."""
        repo = repos.UserRepo(db_session)

        # Create 3 users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(3)
        ]
        created_users = await repo.create_bulk(users_data)

        # Update all users
        updates = [
            (user.id, UserUpdate(first_name=f"Updated{i}")) for i, user in enumerate(created_users)
        ]

        result = await repo.update_bulk(updates)

        assert len(result) == 3
        for i, updated_user in enumerate(result):
            assert updated_user.first_name == f"Updated{i}"

    async def test_update_bulk_custom_column(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test update_bulk with custom column name."""
        repo = repos.UserRepo(db_session)

        # Create users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(2)
        ]
        created_users = await repo.create_bulk(users_data)

        # Update using username as identifier
        updates = [
            (user.username, UserUpdate(first_name=f"NewName{i}"))
            for i, user in enumerate(created_users)
        ]

        result = await repo.update_bulk(updates, id_column_name="username")

        assert len(result) == 2
        for i, updated_user in enumerate(result):
            assert updated_user.first_name == f"NewName{i}"


@pytest.mark.anyio
class TestBaseRepositoryDelete:
    """Test delete operations in BaseRepository."""

    async def test_delete_by_id_not_found(self, db_session: AsyncSession):
        """Test delete_by_id returns False when record not found."""
        repo = repos.UserRepo(db_session)
        non_existent_id = 999999999

        result = await repo.delete_by_id(non_existent_id)

        assert result is False

    async def test_delete_by_id_success(self, db_session: AsyncSession, user: User):
        """Test successful deletion by ID."""
        repo = repos.UserRepo(db_session)
        user_id = user.id

        result = await repo.delete_by_id(user_id)

        assert result is True

        # Verify user is deleted
        deleted_user = await repo.get_by_id(user_id)
        assert deleted_user is None

    async def test_delete_by_id_custom_column(self, db_session: AsyncSession, user: User):
        """Test delete_by_id with custom column name."""
        repo = repos.UserRepo(db_session)
        user_email = user.email

        result = await repo.delete_by_id(user_email, id_column_name="email")

        assert result is True

        # Verify user is deleted
        deleted_user = await repo.get_by_id(user_email, id_column_name="email")
        assert deleted_user is None

    async def test_delete_by_ids_empty(self, db_session: AsyncSession):
        """Test delete_by_ids with empty list returns 0."""
        repo = repos.UserRepo(db_session)

        result = await repo.delete_by_ids([])

        assert result == 0

    async def test_delete_by_ids_partial(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test delete_by_ids with partial deletions (some IDs don't exist)."""
        repo = repos.UserRepo(db_session)

        # Create 2 users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(2)
        ]
        created_users = await repo.create_bulk(users_data)

        # Try to delete 2 existing + 1 non-existent
        non_existent_id = 999999999
        ids_to_delete = [created_users[0].id, non_existent_id, created_users[1].id]

        result = await repo.delete_by_ids(ids_to_delete)

        # Should delete only 2 existing users
        assert result == 2

    async def test_delete_by_ids_success(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test successful bulk deletion."""
        repo = repos.UserRepo(db_session)

        # Create 3 users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(3)
        ]
        created_users = await repo.create_bulk(users_data)
        user_ids = [user.id for user in created_users]

        result = await repo.delete_by_ids(user_ids)

        assert result == 3

        # Verify all users are deleted
        remaining_users = await repo.get_multi_by_ids(obj_ids=user_ids)
        assert len(remaining_users) == 0

    async def test_delete_by_ids_custom_column(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test delete_by_ids with custom column name."""
        repo = repos.UserRepo(db_session)

        # Create users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(2)
        ]
        created_users = await repo.create_bulk(users_data)
        usernames = [user.username for user in created_users]

        result = await repo.delete_by_ids(usernames, id_column_name="username")

        assert result == 2


@pytest.mark.anyio
class TestBaseRepositoryCustomQuery:
    """Test custom query execution in BaseRepository."""

    async def test_custom_query_select(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test custom_query with SELECT statement."""
        repo = repos.UserRepo(db_session)

        # Create a user
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name=faker.last_name(),
        )
        created_user = await repo.create_one(user_data)

        # Execute custom query with schema prefix
        schema = "fastapi_template"  # From config
        query = f'SELECT * FROM {schema}.{User.__tablename__} WHERE "id" = {created_user.id}'
        result = await repo.custom_query(query)

        fetched_row = result.fetchone()
        assert fetched_row is not None

    async def test_custom_query_count(
        self, db_session: AsyncSession, faker: Faker, pre_hashed_password: str
    ):
        """Test custom_query with COUNT statement."""
        repo = repos.UserRepo(db_session)

        # Create multiple users
        users_data = [
            UserCreate(
                email=faker.safe_email(),
                username=faker.user_name(),
                hashed_password=pre_hashed_password,
                first_name=faker.first_name(),
                last_name=faker.last_name(),
            )
            for _ in range(5)
        ]
        await repo.create_bulk(users_data)

        # Count users with schema prefix
        schema = "fastapi_template"  # From config
        query = f"SELECT COUNT(*) FROM {schema}.{User.__tablename__}"
        result = await repo.custom_query(query)

        count = result.scalar()
        assert count is not None
        assert count >= 5
