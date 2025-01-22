from functools import lru_cache
from app.services.pipeline_service import RAGPipelineService
from app.services.embedder_service import EmbedderService
from app.services.qdrant_service import QdrantServcice

_pipeline_service = None

def get_pipeline_service() -> RAGPipelineService:
    global _pipeline_service
    if _pipeline_service is None:
        raise RuntimeError("Pipeline service not initialized")
    return _pipeline_service

async def initialize_pipeline_service(qdrant_client) -> None:
    global _pipeline_service
    qdrant_service = QdrantServcice(client=qdrant_client)
    embedder_service = EmbedderService()
    _pipeline_service = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service
    )