# Bala Aparna - 29485442

"""
Application Constants
Centralized configuration values following best practices
"""
from enum import Enum
from typing import Final

# API Configuration - controls retry behavior for LLM API calls
MAX_RETRIES: Final[int] = 3  # Number of retry attempts on failure
RETRY_DELAY: Final[float] = 1.0  # Initial delay between retries (seconds)
RETRY_BACKOFF: Final[float] = 2.0  # Exponential backoff multiplier
REQUEST_TIMEOUT: Final[int] = 120  # Maximum time for a single API call (seconds)

# Rate Limiting
RATE_LIMIT_CALLS: Final[int] = 60
RATE_LIMIT_PERIOD: Final[int] = 60  # seconds

# Token Limits - controls context window management
DEFAULT_MAX_TOKENS: Final[int] = 4000  # Default max tokens for LLM response
MAX_CONTEXT_TOKENS: Final[int] = 128000  # Max context window size (model dependent)
BUFFER_TOKENS: Final[int] = 500  # Safety buffer to prevent context overflow

# Temperature Settings - lower values = more deterministic, higher = more creative
class Temperature:
    """Temperature values for different agent types (0.0-1.0 scale)"""
    REQUIREMENTS: Final[float] = 0.5  # Moderate creativity for requirements analysis
    ARCHITECT: Final[float] = 0.4  # Balanced for architecture decisions
    DATABASE: Final[float] = 0.3  # Lower for consistent schema generation
    CODER: Final[float] = 0.3  # Lower for reliable code generation
    DOCKER: Final[float] = 0.2  # Very low for deterministic config files
    TESTER: Final[float] = 0.4  # Moderate for test case creativity
    SECURITY: Final[float] = 0.3  # Lower for consistent security checks
    REVIEWER: Final[float] = 0.4  # Moderate for code review insights

# Next.js Configuration
class NextJSConfig:
    """Next.js specific configuration"""
    VERSION: Final[str] = "14.0.4"
    NODE_VERSION: Final[str] = "18-alpine"
    DEFAULT_PORT: Final[int] = 3000
    
# Database Configuration
class DatabaseConfig:
    """Database configuration"""
    POSTGRES_IMAGE: Final[str] = "postgres:15-alpine"
    POSTGRES_PORT: Final[int] = 5432
    MONGODB_IMAGE: Final[str] = "mongo:7-alpine"
    MONGODB_PORT: Final[int] = 27017

# File Generation Limits - bounds for a single generation session
MAX_FILES_PER_GENERATION: Final[int] = 50  # Prevents runaway generation
MIN_FILES_PER_GENERATION: Final[int] = 10  # Ensures minimum viable project

# Validation
MAX_DESCRIPTION_LENGTH: Final[int] = 5000
MIN_DESCRIPTION_LENGTH: Final[int] = 20

# Logging
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Cache Configuration
CACHE_TTL: Final[int] = 3600  # 1 hour
CACHE_MAX_SIZE: Final[int] = 100

# Health Check
HEALTH_CHECK_INTERVAL: Final[int] = 60  # seconds
AGENT_TIMEOUT: Final[int] = 300  # 5 minutes

# Workflow Phases
class WorkflowPhaseNames:
    """Human-readable workflow phase names"""
    DISCOVERY: Final[str] = "Phase 1: Discovery & Analysis"
    DESIGN: Final[str] = "Phase 2: Design & Planning"
    IMPLEMENTATION: Final[str] = "Phase 3: Implementation"
    QA: Final[str] = "Phase 4: Quality Assurance"
    VALIDATION: Final[str] = "Phase 5: Validation"
    # Phase 6 (Monitoring) removed - not needed for core code generation

# Error Messages
class ErrorMessages:
    """Centralized error messages"""
    INVALID_DESCRIPTION: Final[str] = "Description must be between {min} and {max} characters"
    API_TIMEOUT: Final[str] = "Request timed out after {timeout} seconds"
    MAX_RETRIES_EXCEEDED: Final[str] = "Maximum retries ({retries}) exceeded"
    AGENT_FAILED: Final[str] = "Agent {agent_name} failed: {error}"
    INVALID_DATABASE: Final[str] = "Invalid database type: {db_type}. Must be 'auto', 'postgresql', or 'mongodb'"
    RATE_LIMIT_EXCEEDED: Final[str] = "Rate limit exceeded. Please try again in {seconds} seconds"

# Success Messages
class SuccessMessages:
    """Centralized success messages"""
    GENERATION_STARTED: Final[str] = "Code generation started successfully"
    GENERATION_COMPLETED: Final[str] = "Code generation completed successfully"
    AGENT_COMPLETED: Final[str] = "Agent {agent_name} completed successfully"
    FILES_GENERATED: Final[str] = "Generated {count} files successfully"

# Supported Languages (for Monaco Editor)
SUPPORTED_LANGUAGES: Final[list[str]] = [
    "typescript",
    "javascript",
    "json",
    "yaml",
    "markdown",
    "dockerfile",
    "shell",
    "css",
    "scss",
    "html",
]

# Docker Configuration
class DockerConfig:
    """Docker-specific configuration"""
    BUILD_TIMEOUT: Final[int] = 600  # 10 minutes
    COMPOSE_VERSION: Final[str] = "3.8"
    NETWORK_NAME: Final[str] = "app-network"
    
# Security
class SecurityConfig:
    """Security-related configuration"""
    MAX_REQUEST_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
    ALLOWED_ORIGINS: Final[list[str]] = ["http://localhost:3000", "http://localhost:3002"]
    SESSION_TIMEOUT: Final[int] = 3600  # 1 hour

