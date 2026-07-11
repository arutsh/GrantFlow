import pytest


@pytest.fixture
def anyio_backend():
    """Run @pytest.mark.anyio tests on asyncio only.

    anyio's built-in fixture parametrizes every anyio test over both asyncio
    and trio, but this service is asyncio-only and trio isn't installed.
    """
    return "asyncio"
