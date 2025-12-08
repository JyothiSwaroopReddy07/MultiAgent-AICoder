"""
Configuration management
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Gemini Configuration - explicitly loaded from .env
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = "gemini-2.5-pro"  # Using Pro for better code quality
    gemini_fallback_model: str = "gemini-2.5-flash"  # Flash as fallback

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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
