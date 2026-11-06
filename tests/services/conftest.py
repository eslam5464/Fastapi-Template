"""Fixtures shared by every service test package (no third-party SDKs)."""

from pathlib import Path

import pytest
from faker import Faker


@pytest.fixture
def faker_instance() -> Faker:
    """Create a Faker instance for test data generation."""
    return Faker()


@pytest.fixture
def temp_test_file(tmp_path: Path, faker_instance: Faker) -> Path:
    """Create a temporary test file."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text(faker_instance.text())
    return test_file
