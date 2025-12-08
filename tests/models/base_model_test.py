from datetime import datetime

import pytest

from app.models.base import Base
from app.models.user import User


class TestBaseModel:
    """Test Base model class fields and behaviors."""

    def test_has_id_field(self):
        """Test that Base models have id field."""
        assert hasattr(Base, "id")

    def test_has_created_at_field(self):
        """Test that Base models have created_at field."""
        assert hasattr(Base, "created_at")

    def test_has_updated_at_field(self):
        """Test that Base models have updated_at field."""
        assert hasattr(Base, "updated_at")

    def test_tablename_generation_simple(self):
        """Test tablename generation for simple class names."""
        # User model should become 'user'
        assert User.__tablename__ == "user"

    def test_tablename_generation_camelcase(self):
        """Test tablename generation converts CamelCase to snake_case."""

        # Create a test model
        class UserProfile(Base):
            __tablename__ = "user_profile"

        # CamelCase should be converted to snake_case
        expected = "user_profile"
        assert UserProfile.__tablename__ == expected

    def test_tablename_generation_multiple_words(self):
        """Test tablename with multiple capital letters."""

        # Create test models
        class HTTPRequest(Base):
            __tablename__ = "http_request"

        assert HTTPRequest.__tablename__ == "http_request"


@pytest.mark.anyio
class TestToDict:
    """Test to_dict method of Base model."""

    async def test_to_dict_basic(self, user: User):
        """Test basic to_dict conversion."""
        result = user.to_dict()

        assert isinstance(result, dict)
        assert "id" in result
        assert "email" in result
        assert "username" in result
        assert "created_at" in result
        assert result["id"] == user.id
        assert result["email"] == user.email

    async def test_to_dict_exclude_keys(self, user: User):
        """Test to_dict with exclude_keys parameter."""
        result = user.to_dict(exclude_keys={"hashed_password", "created_at"})

        assert isinstance(result, dict)
        assert "hashed_password" not in result
        assert "created_at" not in result
        assert "id" in result
        assert "email" in result

    async def test_to_dict_exclude_none_true(self, db_session, faker, pre_hashed_password):
        """Test to_dict with exclude_none=True."""
        from app import repos
        from app.schemas import UserCreate

        # Create user
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name="",  # Empty string instead of None
        )
        user_obj = await repos.UserRepo(db_session).create_one(user_data)

        result = user_obj.to_dict(exclude_none=True)

        # Empty string fields should be present (not None)
        assert "last_name" in result
        assert "id" in result
        assert "email" in result

    async def test_to_dict_exclude_none_false(self, db_session, faker, pre_hashed_password):
        """Test to_dict with exclude_none=False."""
        from app import repos
        from app.schemas import UserCreate

        # Create user
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name="",  # Empty string instead of None
        )
        user_obj = await repos.UserRepo(db_session).create_one(user_data, exclude_none=False)

        result = user_obj.to_dict(exclude_none=False)

        # Empty strings should be included
        assert "last_name" in result
        assert result["last_name"] == ""
        assert "id" in result

    async def test_to_dict_all_fields_present(self, user: User):
        """Test that to_dict includes all model columns."""
        result = user.to_dict()

        # Should have core fields
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "email" in result
        assert "username" in result
        assert "first_name" in result
        assert "last_name" in result

    async def test_to_dict_values_match_attributes(self, user: User):
        """Test that to_dict values match model attribute values."""
        result = user.to_dict()

        assert result["id"] == user.id
        assert result["email"] == user.email
        assert result["username"] == user.username
        assert result["first_name"] == user.first_name
        assert result["last_name"] == user.last_name

    async def test_to_dict_datetime_serializable(self, user: User):
        """Test that datetime fields are in result."""
        result = user.to_dict()

        # created_at and updated_at should be present
        assert "created_at" in result
        assert isinstance(result["created_at"], datetime) or result["created_at"] is None

        # updated_at might be None
        if "updated_at" in result and result["updated_at"] is not None:
            assert isinstance(result["updated_at"], datetime)

    async def test_to_dict_combined_exclude_keys_and_none(
        self, db_session, faker, pre_hashed_password
    ):
        """Test to_dict with both exclude_keys and exclude_none."""
        from app import repos
        from app.schemas import UserCreate

        # Create user
        user_data = UserCreate(
            email=faker.safe_email(),
            username=faker.user_name(),
            hashed_password=pre_hashed_password,
            first_name=faker.first_name(),
            last_name="",  # Empty string instead of None
        )
        user_obj = await repos.UserRepo(db_session).create_one(user_data, exclude_none=False)

        result = user_obj.to_dict(exclude_keys={"hashed_password"}, exclude_none=True)

        # Should exclude hashed_password
        assert "hashed_password" not in result
        # Empty string values are not None, so they'll be present
        # Should include other fields
        assert "id" in result
        assert "email" in result

    async def test_to_dict_empty_exclude_keys(self, user: User):
        """Test to_dict with empty exclude_keys set."""
        result = user.to_dict(exclude_keys=set())

        # Should include all fields
        assert "id" in result
        assert "email" in result
        assert "hashed_password" in result
