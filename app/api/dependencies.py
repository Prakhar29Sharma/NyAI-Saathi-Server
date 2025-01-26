from functools import lru_cache
from app.services.pipeline_service import RAGPipelineService
from app.services.embedder_service import EmbedderService
from app.services.qdrant_service import QdrantServcice

_pipeline_service_judgement = None
_pipeline_service_laws = None

def get_judgement_pipeline_service() -> RAGPipelineService:
    global _pipeline_service_judgement
    if _pipeline_service_judgement is None:
        raise RuntimeError("Judgement pipeline service not initialized")
    return _pipeline_service_judgement

@lru_cache
async def initialize_judgement_pipeline_service(qdrant_client) -> None:
    global _pipeline_service_judgement
    qdrant_service = QdrantServcice(client=qdrant_client, collection_name="judgement")
    embedder_service = EmbedderService()
    _pipeline_service_judgement = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service,
        type="judgement"
    )

def get_laws_pipeline_service() -> RAGPipelineService:
    global _pipeline_service_laws
    if _pipeline_service_laws is None:
        raise RuntimeError("Laws pipeline service not initialized")
    return _pipeline_service_laws

@lru_cache
async def initialize_laws_pipeline_service(qdrant_client) -> None:
    global _pipeline_service_laws
    qdrant_service = QdrantServcice(client=qdrant_client, collection_name="laws")
    embedder_service = EmbedderService()
    _pipeline_service_laws = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service,
        type="law"
    )