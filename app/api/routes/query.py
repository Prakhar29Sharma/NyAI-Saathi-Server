from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.api.dependencies import get_judgement_pipeline_service
from app.api.dependencies import get_laws_pipeline_service
from app.services.pipeline_service import RAGPipelineService
from app.core.exceptions import QueryProcessingError

router = APIRouter()

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None

class Document(BaseModel):
    content: str
    metadata: DocumentMetadata

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

class QueryResponse(BaseModel):
    answer: str
    documents: List[Document]

@router.post("/query/judgements", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    pipeline_service: RAGPipelineService = Depends(get_judgement_pipeline_service)
) -> QueryResponse:
    try:
        result = await pipeline_service.process_query(request.query)
        if not result or not result.get("answer"):
            raise QueryProcessingError("No results found")
            
        return QueryResponse(
            answer=result["answer"],
            documents=result["documents"]
        )
    except QueryProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )
    
@router.post("/query/laws")
async def query_documents(
    request: QueryRequest,
    pipeline_service: RAGPipelineService = Depends(get_laws_pipeline_service)
) -> QueryResponse:
    try:
        result = await pipeline_service.process_query(request.query)
        print(result)
        if not result or not result.get("answer"):
            raise QueryProcessingError("No results found")
            
        return QueryResponse(
            answer=result["answer"],
            documents=result["documents"]
        )
    except QueryProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )