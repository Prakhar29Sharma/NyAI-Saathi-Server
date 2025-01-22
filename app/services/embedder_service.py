from typing import List, Dict
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import logger

class EmbedderService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def get_document_embeddings(self, documents: List[Dict]) -> List[List[float]]:
        try:
            texts = [doc["content"] for doc in documents]
            embeddings = self.model.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    async def get_query_embedding(self, query: str) -> List[float]:
        try:
            embedding = self.model.encode(query)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise