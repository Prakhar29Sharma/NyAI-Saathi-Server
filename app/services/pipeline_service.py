from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
from haystack.utils import Secret
from app.core.config import settings
from app.core.exceptions import QueryProcessingError
from app.services.embedder_service import EmbedderService
from app.services.qdrant_service import QdrantServcice

class RAGPipelineService:
    def __init__(self, qdrant_service: QdrantServcice, embedder_service: EmbedderService):
        self.qdrant_service = qdrant_service
        self.embedder_service = embedder_service
        self.pipeline = self._create_pipeline()
    
    def _create_pipeline(self):
        prompt_template = """
        You're a legal research assistant and given the following context of judgement,
        answer the user query and also provide references / document links for the 
        verification.
        context : 
        {% for document in documents %}
        {{ document.content }}
        {% endfor %}

        Question: {{question}}
        Answer:
        """

        prompt_builder = PromptBuilder(template=prompt_template)
        
        pipeline = Pipeline()
        pipeline.add_component("prompt_builder", prompt_builder)
        pipeline.add_component("llm", GoogleAIGeminiGenerator(
            model="gemini-1.5-flash-latest",
            api_key=Secret.from_token(settings.GOOGLE_API_KEY)
        ))
        
        pipeline.connect("prompt_builder", "llm")
        return pipeline
    
    async def process_query(self, query: str) -> dict:
        try:
            query_embedding = await self.embedder_service.get_query_embedding(query)
            search_results = await self.qdrant_service.search_similar(query_embedding)

            pipeline_input = {
                "prompt_builder": {
                    "question": query,
                    "documents": [
                        {"content": result.payload["content"]} for result in search_results
                    ]
                }
            }

            result = self.pipeline.run(pipeline_input)

            print(result)

            return {
                "answer": result["llm"]["replies"][0],
                "documents": [
                    {
                        "content": result.payload["content"],
                        "metadata": result.payload.get("metadata", {})
                    } for result in search_results
                ]
            }
        except Exception as e:
            raise QueryProcessingError(f"Pipeline execution failed: {str(e)}")

