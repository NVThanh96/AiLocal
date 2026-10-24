import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Local AI Agent Workspace"
    APP_VERSION: str = "0.1.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    
    # Workspace & Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    DATABASE_PATH: Path = STORAGE_DIR / "workspace.db"
    TEMP_SANDBOX_DIR: Path = BASE_DIR / "temp_test_runs"
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    PRIMARY_MODEL: str = "qwen3:4b"
    CODING_MODEL: str = "qwen2.5-coder:7b"
    
    # Security Policies
    ENABLE_STRICT_WORKSPACE_ISOLATION: bool = True
    MAX_FILE_READ_BYTES: int = 2 * 1024 * 1024  # 2 MB limit per file in chat context

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure required directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
