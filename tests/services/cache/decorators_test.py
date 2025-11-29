from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache.decorators import cache_result


class TestCacheResultDecorator:
    """Test cache_result decorator."""

    @pytest.mark.anyio
    async def test_cache_result_cache_miss(self):
        """Test cache_result with cache miss."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock()

        with patch("app.services.cache.cache_manager", mock_cache_manager):

            @cache_result(expire=60, key_prefix="test")
            async def test_function(value: int) -> int:
                return value * 2

            result = await test_function(5)

            assert result == 10
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_result_cache_hit(self):
        """Test cache_result with cache hit."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=20)
        mock_cache_manager.set = AsyncMock()

        with patch("app.services.cache.cache_manager", mock_cache_manager):

            @cache_result(expire=60, key_prefix="test")
            async def test_function(value: int) -> int:
                return value * 2

            result = await test_function(10)

            assert result == 20
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_not_called()

    @pytest.mark.anyio
    async def test_cache_result_with_default_params(self):
        """Test cache_result with default parameters."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock()

        with patch("app.services.cache.cache_manager", mock_cache_manager):

            @cache_result()
            async def test_function(value: str) -> str:
                return value.upper()

            result = await test_function("hello")

            assert result == "HELLO"
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_result_with_kwargs(self):
        """Test cache_result with keyword arguments."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock()

        with patch("app.services.cache.cache_manager", mock_cache_manager):

            @cache_result(expire=120)
            async def test_function(a: int, b: int, c: int = 0) -> int:
                return a + b + c

            result = await test_function(1, 2, c=3)

            assert result == 6
            mock_cache_manager.get.assert_called_once()
            mock_cache_manager.set.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_result_key_generation(self):
        """Test cache_result generates unique keys for different calls."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock()

        with patch("app.services.cache.cache_manager", mock_cache_manager):

            @cache_result(key_prefix="calc")
            async def test_function(x: int, y: int) -> int:
                return x + y

            await test_function(1, 2)
            await test_function(3, 4)

            assert mock_cache_manager.get.call_count == 2
            assert mock_cache_manager.set.call_count == 2

            # Verify different keys were generated
            call_args_1 = mock_cache_manager.get.call_args_list[0][0][0]
            call_args_2 = mock_cache_manager.get.call_args_list[1][0][0]
            assert call_args_1 != call_args_2
