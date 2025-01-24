from functools import lru_cache
from app.services.pipeline_service import RAGPipelineService
from app.services.embedder_service import EmbedderService
from app.services.qdrant_service import QdrantServcice

_pipeline_service = None
_pipeline_service_llama = None
_pipeline_service_mixtral = None

def get_pipeline_service(llm: str = "gemini") -> RAGPipelineService:
    global _pipeline_service, _pipeline_service_llama, _pipeline_service_mixtral
    
    if llm == "llama":
        if _pipeline_service_llama is None:
            raise RuntimeError("Llama pipeline service not initialized")
        return _pipeline_service_llama
    elif llm == "mistral":
        if _pipeline_service_mixtral is None:
            raise RuntimeError("Mistral pipeline service not initialized")
        return _pipeline_service_mixtral
    else:
        if _pipeline_service is None:
            raise RuntimeError("Gemini pipeline service not initialized")
        return _pipeline_service

async def initialize_pipeline_service(qdrant_client) -> None:
    global _pipeline_service
    qdrant_service = QdrantServcice(client=qdrant_client)
    embedder_service = EmbedderService()
    _pipeline_service = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service
    )

async def initialize_pipeline_service_with_llama(qdrant_client) -> None:
    global _pipeline_service_llama
    qdrant_service = QdrantServcice(client=qdrant_client)
    embedder_service = EmbedderService()
    _pipeline_service_llama = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service,
        llm="llama"
    )

async def initialize_pipeline_service_with_mixtral(qdrant_client) -> None:
    global _pipeline_service_mixtral
    qdrant_service = QdrantServcice(client=qdrant_client)
    embedder_service = EmbedderService()
    _pipeline_service_mixtral = RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service,
        llm="mixtral"
    )