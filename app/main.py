from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies.qdrant import get_qdrant_client
from app.api.dependencies import initialize_judgement_pipeline_service, initialize_laws_pipeline_service
from app.api.routes import query

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # client
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_events():
    print(f"GOOGLE_API_KEY configured: {bool(settings.GOOGLE_API_KEY)}")
    # First initialize Qdrant client
    qdrant_client = await get_qdrant_client()
    # Then initialize pipeline service
    await initialize_judgement_pipeline_service(qdrant_client)
    await initialize_laws_pipeline_service(qdrant_client)
    return {"status": "initialized"}
    
app.include_router(query.router, prefix="/api/v1")

@app.get('/health')
async def health_check():
    return { "status": "healthy" }