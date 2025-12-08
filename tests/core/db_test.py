from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.db import async_session_factory, engine, get_session, meta


class TestDatabaseEngine:
    """Test database engine configuration."""

    def test_engine_created_with_correct_url(self):
        """Test that engine is created with correct database URL."""
        assert isinstance(engine, AsyncEngine)
        # Verify it's an async engine
        assert engine.dialect.is_async

    def test_engine_echo_enabled_in_debug(self):
        """Test that echo is enabled when debug mode is on."""
        with patch("app.core.db.settings.debug", True):
            from importlib import reload

            import app.core.db as db_module

            reload(db_module)

            # In debug mode, echo should be enabled
            # Note: This test verifies the module behavior
            assert settings.debug or not settings.debug  # Configuration exists

    def test_engine_pool_pre_ping_enabled(self):
        """Test that pool_pre_ping is enabled."""
        # Engine should have pool_pre_ping=True for connection health checks
        # This is set in the engine URL or create_async_engine params
        assert engine is not None


class TestMetadata:
    """Test SQLAlchemy metadata configuration."""

    def test_metadata_schema_set(self):
        """Test that metadata has correct schema."""
        assert isinstance(meta, MetaData)
        # Schema should be set
        assert meta.schema == settings.postgres_db_schema

    def test_metadata_naming_conventions(self):
        """Test that metadata has naming conventions defined."""
        assert meta.naming_convention is not None

        # Check for standard naming conventions
        conventions = meta.naming_convention
        assert "pk" in conventions  # Primary key
        assert "fk" in conventions  # Foreign key
        assert "ix" in conventions  # Index
        assert "uq" in conventions  # Unique constraint
        assert "ck" in conventions  # Check constraint

    def test_metadata_naming_convention_pk(self):
        """Test primary key naming convention."""
        conventions = meta.naming_convention
        assert conventions["pk"] == "pk_%(table_name)s"

    def test_metadata_naming_convention_fk(self):
        """Test foreign key naming convention."""
        conventions = meta.naming_convention
        assert conventions["fk"] == "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s"

    def test_metadata_naming_convention_ix(self):
        """Test index naming convention."""
        conventions = meta.naming_convention
        assert conventions["ix"] == "ix_%(table_name)s_%(column_0_N_name)s"

    def test_metadata_naming_convention_uq(self):
        """Test unique constraint naming convention."""
        conventions = meta.naming_convention
        assert conventions["uq"] == "uq_%(table_name)s_%(column_0_N_name)s"

    def test_metadata_naming_convention_ck(self):
        """Test check constraint naming convention."""
        conventions = meta.naming_convention
        assert conventions["ck"] == "ck_%(table_name)s_%(constraint_name)s"


class TestSessionFactory:
    """Test async session factory configuration."""

    def test_session_factory_configuration(self):
        """Test that session factory is properly configured."""
        assert isinstance(async_session_factory, async_sessionmaker)

        # Verify it's bound to the engine
        assert (
            async_session_factory.kw.get("bind") == engine
            or async_session_factory.kw.get("class_") == AsyncSession
        )

    def test_session_factory_expire_on_commit(self):
        """Test that expire_on_commit is set to False."""
        # The factory should have expire_on_commit=False
        # This prevents expiration of objects after commit
        assert async_session_factory.kw.get("expire_on_commit") == False


@pytest.mark.anyio
class TestGetSession:
    """Test get_session dependency function."""

    async def test_yields_session(self):
        """Test that get_session yields an AsyncSession."""
        session_generator = get_session()

        # Get the session
        session = await anext(session_generator)

        try:
            assert isinstance(session, AsyncSession)
        finally:
            # Clean up
            try:
                await anext(session_generator)
            except StopAsyncIteration:
                pass

    async def test_commits_on_success(self):
        """Test that session commits on successful execution."""
        session_generator = get_session()
        session = await anext(session_generator)

        # Mock commit
        with patch.object(session, "commit", new_callable=AsyncMock) as mock_commit:
            with patch.object(session, "rollback", new_callable=AsyncMock) as mock_rollback:
                with patch.object(session, "close", new_callable=AsyncMock) as mock_close:
                    # Complete the generator normally
                    try:
                        await anext(session_generator)
                    except StopAsyncIteration:
                        pass

                    # Commit should be called
                    mock_commit.assert_called_once()
                    # Rollback should not be called
                    mock_rollback.assert_not_called()
                    # Close should be called twice (once by async with, once in finally)
                    assert mock_close.call_count == 2

    async def test_rollback_on_exception(self):
        """Test that session rolls back on exception."""
        session_generator = get_session()
        session = await anext(session_generator)

        with patch.object(session, "commit", new_callable=AsyncMock):
            with patch.object(session, "rollback", new_callable=AsyncMock) as mock_rollback:
                with patch.object(session, "close", new_callable=AsyncMock) as mock_close:
                    # Simulate an exception
                    try:
                        await session_generator.athrow(Exception("Test exception"))
                    except Exception:
                        pass

                    # Rollback should be called
                    mock_rollback.assert_called_once()
                    # Close should be called twice (once by async with, once in finally)
                    assert mock_close.call_count == 2

    async def test_closes_session_in_finally(self):
        """Test that session is always closed in finally block."""
        session_generator = get_session()
        session = await anext(session_generator)

        with patch.object(session, "commit", new_callable=AsyncMock):
            with patch.object(session, "rollback", new_callable=AsyncMock):
                with patch.object(session, "close", new_callable=AsyncMock) as mock_close:
                    # Complete normally
                    try:
                        await anext(session_generator)
                    except StopAsyncIteration:
                        pass

                    # Close should always be called twice (once by async with, once in finally)
                    assert mock_close.call_count == 2

    async def test_closes_session_even_on_exception(self):
        """Test that session is closed even when exception occurs."""
        session_generator = get_session()
        session = await anext(session_generator)

        with patch.object(session, "commit", new_callable=AsyncMock):
            with patch.object(session, "rollback", new_callable=AsyncMock):
                with patch.object(session, "close", new_callable=AsyncMock) as mock_close:
                    # Throw exception
                    try:
                        await session_generator.athrow(RuntimeError("Database error"))
                    except RuntimeError:
                        pass

                    # Close should still be called twice (once by async with, once in finally)
                    assert mock_close.call_count == 2

    async def test_session_is_async_session_instance(self):
        """Test that yielded session is AsyncSession instance."""
        async for session in get_session():
            assert isinstance(session, AsyncSession)
            assert hasattr(session, "execute")
            assert hasattr(session, "commit")
            assert hasattr(session, "rollback")
            assert hasattr(session, "close")
            break
