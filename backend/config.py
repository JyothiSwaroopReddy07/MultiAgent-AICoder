"""
Configuration management
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_fallback_model: str = "gpt-3.5-turbo"

    # Server Configuration
    backend_port: int = 8000
    frontend_port: int = 3002
    debug: bool = True
    cors_origins: list = ["http://localhost:3002", "http://127.0.0.1:3002", "http://localhost:3000", "http://127.0.0.1:3000"]

    # MCP Configuration
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 5000

    # Code Generation Settings
    max_tokens: int = 4000
    temperature: float = 0.7
    max_retries: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
