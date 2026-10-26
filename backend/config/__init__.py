"""Portable configuration; no AWS credentials are used."""
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/aria.db"
    llm_provider: str = "groq"
    llm_model: str = "qwen/qwen3.8-27b"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    ollama_host: str = "http://localhost:11434"
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = "aria-api"
    service_secret: str = ""
    allowed_origins: str = "http://localhost:5173"
    adapter_api_url: str = "http://localhost:8000/api/erp"
    storage_path: str = "./data/documents"
    job_timeout_seconds: int = 900
    max_tool_calls: int = 40
    max_output_tokens: int = 2048
    erpnext_url: str = ""
settings = Settings()
