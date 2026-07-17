import pytest


@pytest.fixture
def anyio_backend():
    """Run @pytest.mark.anyio tests on asyncio only (trio isn't installed)."""
    return "asyncio"
