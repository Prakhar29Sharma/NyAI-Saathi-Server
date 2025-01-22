import pytest
import asyncio
from app.dependencies.qdrant import check_connection

@pytest.mark.asyncio
async def test_qdrant_connection():
    assert await check_connection() == True