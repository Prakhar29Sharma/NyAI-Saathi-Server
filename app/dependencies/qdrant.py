from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from app.core.config import settings
from app.core.logging import logger
from app.services.dataset_service import DatasetService
from functools import lru_cache
from app.services.pipeline_service import RAGPipelineService
from app.services.qdrant_service import QdrantServcice
from app.services.embedder_service import EmbedderService

async def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
    try:
        client.get_collection(settings.COLLECTION_NAME)
        print(f'Qdrant connection successfull!\nCollection {settings.COLLECTION_NAME} exist')
    except:
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        logger.info(f'Created collection {settings.COLLECTION_NAME}')
        await initialize_collection_with_data(client)
    return client

async def check_connection() -> bool:
    client = await get_qdrant_client()
    try:
        client.get_collections()
        print('Qdrant vector store connection established')
        return True
    except:
        print('Qdrant vector store connection failed...')
        return False
    
async def initialize_collection_with_data(client: QdrantClient):
    collection_info = client.get_collection(settings.COLLECTION_NAME)
    if collection_info.points_count > 0:
        logger.info(f'Collection {settings.COLLECTION_NAME} already contains documents')
        return
    logger.info('Starting initial dataset upload process...')
    await DatasetService.load_judgements_dataset(client)

@lru_cache()
async def get_pipeline_service() -> RAGPipelineService:
    # Get Qdrant client asynchronously
    qdrant_client = await get_qdrant_client()
    
    # Initialize services
    qdrant_service = QdrantServcice(client=qdrant_client)
    embedder_service = EmbedderService()
    
    return RAGPipelineService(
        qdrant_service=qdrant_service,
        embedder_service=embedder_service
    )
