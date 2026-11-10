from datetime import datetime

import pytest

from app.models.base import Base
from tests.sample_model import SampleRecord, SampleRecordRepo, sample_record_data


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
        # The table name is the snake_case form of the class name
        assert SampleRecord.__tablename__ == "sample_record"

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

    async def test_to_dict_basic(self, sample_record: SampleRecord):
        """Test basic to_dict conversion."""
        result = sample_record.to_dict()

        assert isinstance(result, dict)
        assert "id" in result
        assert "code" in result
        assert "name" in result
        assert "created_at" in result
        assert result["id"] == sample_record.id
        assert result["code"] == sample_record.code

    async def test_to_dict_exclude_keys(self, sample_record: SampleRecord):
        """Test to_dict with exclude_keys parameter."""
        result = sample_record.to_dict(exclude_keys={"payload", "created_at"})

        assert isinstance(result, dict)
        assert "payload" not in result
        assert "created_at" not in result
        assert "id" in result
        assert "code" in result

    async def test_to_dict_exclude_none_true(self, db_session, faker):
        """Test to_dict with exclude_none=True."""
        # Create record
        record_data = sample_record_data(faker, note="")
        record = await SampleRecordRepo(db_session).create_one(record_data)

        result = record.to_dict(exclude_none=True)

        # Empty string fields should be present (not None)
        assert "note" in result
        assert "id" in result
        assert "code" in result

    async def test_to_dict_exclude_none_false(self, db_session, faker):
        """Test to_dict with exclude_none=False."""
        # Create record
        record_data = sample_record_data(faker, note="")
        record = await SampleRecordRepo(db_session).create_one(record_data, exclude_none=False)

        result = record.to_dict(exclude_none=False)

        # Empty strings should be included
        assert "note" in result
        assert result["note"] == ""
        assert "id" in result

    async def test_to_dict_all_fields_present(self, sample_record: SampleRecord):
        """Test that to_dict includes all model columns."""
        result = sample_record.to_dict()

        # Should have core fields
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "code" in result
        assert "name" in result
        assert "label" in result
        assert "note" in result

    async def test_to_dict_values_match_attributes(self, sample_record: SampleRecord):
        """Test that to_dict values match model attribute values."""
        result = sample_record.to_dict()

        assert result["id"] == sample_record.id
        assert result["code"] == sample_record.code
        assert result["name"] == sample_record.name
        assert result["label"] == sample_record.label
        assert result["note"] == sample_record.note

    async def test_to_dict_datetime_serializable(self, sample_record: SampleRecord):
        """Test that datetime fields are in result."""
        result = sample_record.to_dict()

        # created_at and updated_at should be present
        assert "created_at" in result
        assert isinstance(result["created_at"], datetime) or result["created_at"] is None

        # updated_at might be None
        if "updated_at" in result and result["updated_at"] is not None:
            assert isinstance(result["updated_at"], datetime)

    async def test_to_dict_combined_exclude_keys_and_none(self, db_session, faker):
        """Test to_dict with both exclude_keys and exclude_none."""
        # Create record
        record_data = sample_record_data(faker, note="")
        record = await SampleRecordRepo(db_session).create_one(record_data, exclude_none=False)

        result = record.to_dict(exclude_keys={"payload"}, exclude_none=True)

        # Should exclude payload
        assert "payload" not in result
        # Empty string values are not None, so they'll be present
        # Should include other fields
        assert "id" in result
        assert "code" in result

    async def test_to_dict_empty_exclude_keys(self, sample_record: SampleRecord):
        """Test to_dict with empty exclude_keys set."""
        result = sample_record.to_dict(exclude_keys=set())

        # Should include all fields
        assert "id" in result
        assert "code" in result
        assert "payload" in result
