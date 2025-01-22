from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NyAI Saathi"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: str = "6333"
    COLLECTION_NAME: str = "legal_documents"
    VECTOR_SIZE: int = 384
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    GOOGLE_API_KEY: str
    LLAMA3_API_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()
