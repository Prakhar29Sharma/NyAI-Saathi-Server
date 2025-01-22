import pytest
from app.dependencies.qdrant import get_qdrant_client
from app.core.config import settings

@pytest.mark.asyncio
async def test_dataset_loading():
    client = await get_qdrant_client()
    try:
        collection_info = client.get_collection(settings.COLLECTION_NAME)
        assert collection_info.points_count > 0
    except:
        assert False