from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.api.dependencies import get_judgement_pipeline_service, get_laws_pipeline_service
from app.services.pipeline_service import RAGPipelineService
from app.services.global_pipeline_monitor import GlobalPipelineMonitor
from app.core.exceptions import QueryProcessingError
from app.core.logging import logger
import time

router = APIRouter(prefix="/query")

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None

class Document(BaseModel):
    content: str
    metadata: DocumentMetadata

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    documents: List[Dict[str, Any]] = []
    time_taken: float

async def monitored_process_query(
    query_text: str, 
    pipeline_service: RAGPipelineService,
    pipeline_type: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process a query while monitoring and broadcasting pipeline events."""
    start_time = time.time()
    
    # Get the global pipeline monitor
    monitor = GlobalPipelineMonitor()
    
    try:
        # Notify that a new query is being processed
        await monitor.new_query(query_text, pipeline_type, user_id)
        
        # Track embedding generation
        embedding_start = time.time()
        await monitor.start_embedding()
        query_embedding = await pipeline_service.embedder_service.get_query_embedding(query_text)
        embedding_end = time.time()
        embedding_time_ms = (embedding_end - embedding_start) * 1000
        await monitor.complete_embedding(len(query_embedding), embedding_time_ms)
        
        # Track vector search
        search_start = time.time()
        await monitor.start_search()
        search_results = await pipeline_service.qdrant_service.search_similar(query_embedding)
        search_end = time.time()
        search_time_ms = (search_end - search_start) * 1000
        await monitor.complete_search(len(search_results), search_time_ms)
        
        # Track context building
        context_start = time.time()
        await monitor.start_context_building()
        pipeline_input = {
            "prompt_builder": {
                "question": query_text,
                "documents": [
                    {"content": result.payload["content"]} for result in search_results
                ]
            }
        }
        
        # Calculate combined context size
        combined_context = "\n".join([result.payload["content"] for result in search_results])
        context_end = time.time()
        context_time_ms = (context_end - context_start) * 1000
        await monitor.complete_context_building(combined_context, context_time_ms)
        
        # Track LLM generation
        llm_start = time.time()
        await monitor.start_llm_generation()
        result = pipeline_service.pipeline.run(pipeline_input)
        answer = result["llm"]["replies"][0]
        llm_end = time.time()
        llm_time_ms = (llm_end - llm_start) * 1000
        await monitor.complete_llm_generation(answer, llm_time_ms)
        
        response = {
            "answer": answer,
            "documents": [
                {
                    "content": result.payload["content"],
                    "metadata": result.payload.get("metadata", {})
                } for result in search_results
            ]
        }
        
        # Complete the pipeline
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000

        # Collect all stage metrics
        stage_metrics = {
            "embedding": embedding_time_ms,
            "search": search_time_ms,
            "context": context_time_ms,
            "llm": llm_time_ms
        }

        # Record query info for reference
        query_info = {
            "query": query_text,
            "pipeline_type": pipeline_type
        }

        await monitor.complete_pipeline(
            answer, 
            total_time_ms,
            stage_metrics,
            query_info
        )
        
        # Add time_taken to response
        response["time_taken"] = end_time - start_time
        
        return response
        
    except Exception as e:
        error_message = f"Pipeline execution failed: {str(e)}"
        logger.error(error_message)
        await monitor.report_error(error_message)
        raise QueryProcessingError(error_message)

@router.post("/judgements", response_model=QueryResponse)
async def query_judgements(
    request: QueryRequest,
    pipeline_service: RAGPipelineService = Depends(get_judgement_pipeline_service)
):
    """
    Process a query against Indian judgements with RAG.
    """
    try:
        result = await monitored_process_query(
            request.query, 
            pipeline_service,
            "judgement",
            request.user_id
        )
        return result
    except QueryProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/laws", response_model=QueryResponse)
async def query_laws(
    request: QueryRequest,
    pipeline_service: RAGPipelineService = Depends(get_laws_pipeline_service)
):
    """
    Process a query against Indian laws with RAG.
    """
    try:
        result = await monitored_process_query(
            request.query, 
            pipeline_service,
            "laws",
            request.user_id
        )
        return result
    except QueryProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))