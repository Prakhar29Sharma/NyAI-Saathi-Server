from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies.qdrant import get_qdrant_client
from app.api.dependencies import initialize_judgement_pipeline_service, initialize_laws_pipeline_service
from app.api.routes import query  # Import the query router
from app.api.routes import pipeline_visualization  # Import the pipeline visualization router
import os

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nyaisaathi.tech/", "https://nyaisaathi.tech/*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/api/static", StaticFiles(directory="/var/www/nyai-static"), name="static")

@app.on_event("startup")
async def startup_events():
    print(f"GOOGLE_API_KEY configured: {bool(settings.GOOGLE_API_KEY)}")
    # First initialize Qdrant client
    qdrant_client = await get_qdrant_client()
    # Then initialize pipeline service
    await initialize_judgement_pipeline_service(qdrant_client)
    await initialize_laws_pipeline_service(qdrant_client)
    return {"status": "initialized"}

# Include routers with the correct prefix
app.include_router(query.router, prefix="/v1")  # This will result in /api/v1/query/laws
app.include_router(pipeline_visualization.router, prefix="/v1")

@app.get('/health')
async def health_check():
    return { "status": "healthy" }