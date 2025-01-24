from fastapi import FastAPI
from app.core.config import settings
from app.dependencies.qdrant import get_qdrant_client
from app.api.dependencies import initialize_pipeline_service
from app.api.dependencies import initialize_pipeline_service_with_mixtral
from app.api.dependencies import initialize_pipeline_service_with_llama
from app.api.routes import query

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
async def startup_events():
    print(f"GOOGLE_API_KEY configured: {bool(settings.GOOGLE_API_KEY)}")
    # First initialize Qdrant client
    qdrant_client = await get_qdrant_client()
    # Then initialize pipeline services for different models
    await initialize_pipeline_service(qdrant_client)
    await initialize_pipeline_service_with_llama(qdrant_client)
    await initialize_pipeline_service_with_mixtral(qdrant_client)
    return {"status": "initialized"}
    
app.include_router(query.router, prefix="/api/v1")

@app.get('/health')
async def health_check():
    return { "status": "healthy" }