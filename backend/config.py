"""
Configuration management
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Gemini Configuration  
    gemini_api_key: str = "AIzaSyD-CwCrZHZHw4Nc32OCYe0G2WUNntg_S28"
    gemini_model: str = "gemini-2.5-flash"  # Updated to valid model
    gemini_fallback_model: str = "gemini-2.0-flash"  # Fallback model

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
        extra = "ignore"  # Ignore extra fields (backward compatibility)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
