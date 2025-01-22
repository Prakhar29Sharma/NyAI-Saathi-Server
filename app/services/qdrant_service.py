from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict
from app.core.config import settings
from app.core.logging import logger


class QdrantServcice:
    def __init__(self, client: QdrantClient):
        self.client = client

    async def search_similar(self, query_vector: List[float], top_k: int = 10):
        return self.client.search(
            collection_name=settings.COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )