from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from app.core.config import settings
from app.core.logging import logger
from app.services.dataset_service import DatasetService

async def get_qdrant_client() -> QdrantClient:
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
    try:
        client.get_collection(settings.COLLECTION_NAME)
        print(f'Qdrant connection successfull!\nCollection {settings.COLLECTION_NAME} exist')
        client.get_collection(settings.COLLECTION_NAME2)
        print(f'Collection {settings.COLLECTION_NAME2} exist')
    except:
        if not client.collection_exists(settings.COLLECTION_NAME):
            client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            logger.info(f'Created collection {settings.COLLECTION_NAME}')
         
        
        if not client.collection_exists(settings.COLLECTION_NAME2):
            client.create_collection(
                collection_name=settings.COLLECTION_NAME2,
                vectors_config=VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            logger.info(f'Created collection {settings.COLLECTION_NAME2}')
        

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
    else: 
        logger.info('Starting judgement dataset upload process...')
        await DatasetService.load_judgements_dataset(client)

    collection_info = client.get_collection(settings.COLLECTION_NAME2)
    if collection_info.points_count > 0:
        logger.info(f'Collection {settings.COLLECTION_NAME2} already contains documents')
        return
    logger.info('Starting laws dataset upload process...')
    await DatasetService.load_indian_laws_dataset(client)

