import hashlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cache.decorators import build_cache_key, cache_result


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


async def _sample(a: int, b: str = "x") -> str:
    return f"{a}{b}"


class TestBuildCacheKey:
    """build_cache_key must give the same key for the same call in every process."""

    def test_key_format(self):
        digest = hashlib.sha256((repr((1,)) + repr([("b", "y")])).encode("utf-8")).hexdigest()

        key = build_cache_key("prefix", _sample, (1,), {"b": "y"})

        assert key == f"prefix:{__name__}._sample:{digest}"

    def test_kwargs_order_does_not_matter(self):
        assert build_cache_key("p", _sample, (), {"a": 1, "b": "y"}) == build_cache_key(
            "p", _sample, (), {"b": "y", "a": 1}
        )

    def test_different_arguments_give_different_keys(self):
        assert build_cache_key("p", _sample, (1,), {}) != build_cache_key("p", _sample, (2,), {})

    def test_same_name_in_another_scope_gets_its_own_key(self):
        async def _sample(a: int, b: str = "x") -> str:  # same __name__ as the module-level one
            return ""

        module_level = globals()["_sample"]
        assert build_cache_key("p", _sample, (1,), {}) != build_cache_key("p", module_level, (1,), {})

    def test_key_is_identical_across_processes(self):
        """Every worker (and every restart) must compute the same key; hash() would not."""
        code = (
            "from app.services.cache.decorators import build_cache_key\n"
            "def get_user(user_id, *, fields=None): ...\n"
            "print(build_cache_key('users', get_user, ('abc', 42), {'fields': ('name', 'email')}))\n"
        )
        project_root = Path(__file__).resolve().parents[3]
        keys = set()
        for seed in ("1", "2", "3"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            keys.add(result.stdout.strip().splitlines()[-1])

        assert len(keys) == 1, keys
