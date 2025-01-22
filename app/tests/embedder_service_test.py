import pytest
from app.services.embedder_service import EmbedderService
from app.core.config import settings

@pytest.mark.asyncio
async def test_embeddings():
    embedder = EmbedderService()
    query = "test query"
    embedding = await embedder.get_query_embedding(query)
    assert len(embedding) == settings.VECTOR_SIZE