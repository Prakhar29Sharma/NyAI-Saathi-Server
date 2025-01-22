import itertools
from datasets import load_dataset
from haystack import Document
from app.core.config import settings
from huggingface_hub import login
from app.core.logging import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict

from app.services.embedder_service import EmbedderService

class DatasetService:
    @staticmethod
    async def load_judgements_dataset(client: QdrantClient):
        try:
            logger.info("Starting dataset loading from Hugging Face...")
            # Login to Hugging Face
            login(token=settings.HUGGINGFACE_TOKEN)
            
            # Load dataset
            logger.info("Fetching InJudgements dataset...")
            dataset = load_dataset(
                "opennyaiorg/InJudgements_dataset", 
                split="train", 
                streaming=True
            )
            
            batch_size = 100
            batch_count = 0

            # Initialize embedder service
            embedder = EmbedderService()

            for batch in batched(dataset, batch_size):
                logger.info(f"Processing batch {batch_count + 1}...")
                docs = [
                    Document(
                        content=f"Title: {doc['Titles']} Court name: {doc['Court_Name']} "
                               f"Judgement Text: {doc['Text']} Case type: {doc['Case_Type']} "
                               f"Court type: {doc['Court_Type']} Doc_url (reference): {doc['Doc_url']}", 
                        meta={
                            "Titles": doc["Titles"],
                            "Doc_url": doc["Doc_url"], 
                            "Doc_size": doc["Doc_size"]
                        }
                    ) for doc in batch
                ]

                # Get embeddings
                
                embeddings = await embedder.get_document_embeddings([{"content": doc.content} for doc in docs])

                ids = [idx for idx in range(batch_count * batch_size, (batch_count + 1) * batch_size)]
                vectors = embeddings
                payloads = [{"content": doc.content, "metadata": doc.meta} for doc in docs]

                client.upsert(
                    collection_name=settings.COLLECTION_NAME,
                    points=models.Batch(
                        ids=ids,
                        vectors=vectors,
                        payloads=payloads,
                    ),
                )

                batch_count += 1

            logger.info("Initial dataset upload done")
        except Exception as e:
            logger.error(f"Failed to load dataset: {str(e)}")
            raise

def batched(iterable, n):
    it = iter(iterable)
    while True:
        batch = list(itertools.islice(it, n))
        if not batch:
            break
        yield batch