"""Redis client fixtures for the cache service tests."""

from unittest.mock import AsyncMock, Mock

import pytest
from redis.asyncio import ConnectionPool, Redis


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create a mock Redis client."""
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.pipeline = Mock()
    mock_redis.close = AsyncMock()

    # Setup pipeline mock
    mock_pipeline = AsyncMock()
    mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
    mock_pipeline.zadd = Mock(return_value=mock_pipeline)
    mock_pipeline.zcard = Mock(return_value=mock_pipeline)
    mock_pipeline.expire = Mock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[0, 1, 5, True])
    mock_redis.pipeline.return_value = mock_pipeline

    return mock_redis


@pytest.fixture
def mock_redis_pool() -> Mock:
    """Create a mock Redis ConnectionPool."""
    mock_pool = Mock(spec=ConnectionPool)
    mock_pool.connection_kwargs = {"protocol": "2"}
    return mock_pool
