import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core App Settings
    APP_NAME: str = "AI Agent Builder"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM Settings
    LLM_PROVIDER: str = Field(default="ollama", description="Provider: ollama, openai, or mock")
    LLM_MODEL: str = Field(default="llama3:latest", description="Model name (e.g. llama3, gpt-4o, etc.)")
    LLM_TEMPERATURE: float = Field(default=0.2, description="Sampling temperature")

    # Provider Specific URLs / Keys
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI or compatible endpoint base URL")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama API base URL")

    # Loop Guardrails
    MAX_ITERATIONS: int = Field(default=10, description="Max total planning/execution iterations")
    MAX_STEP_RETRIES: int = Field(default=2, description="Max retries for a single step on failure")
    STEP_TIMEOUT_SECONDS: int = Field(default=60, description="Tool execution timeout in seconds")

    # File and Workspace Directories
    WORKSPACE_DIR: str = Field(default="./workspace", description="Safe directory where tools read/write files")
    
    # Memory
    MEMORY_BACKEND: str = Field(default="in_memory", description="Memory backend: in_memory or chromadb")

    @property
    def workspace_path(self) -> Path:
        path = Path(self.WORKSPACE_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
