"""
Example Configuration File
Copy this to config.py and fill in your environment variables
Or use environment variables directly via .env file
"""

# ============================================================================
# REQUIRED CONFIGURATION
# ============================================================================

# Gemini API Key (REQUIRED)
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyD-CwCrZHZHw4Nc32OCYe0G2WUNntg_S28"

# Gemini Model Selection
GEMINI_MODEL = "gemini-pro"  # Primary model (recommended: gemini-pro, gemini-1.5-pro)
GEMINI_FALLBACK_MODEL = "gemini-pro"  # Fallback model for cost efficiency

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Server Ports
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# Environment
ENVIRONMENT = "development"  # development, staging, production
DEBUG = True  # Set to False in production

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Temperature: Controls randomness (0.0-2.0)
# - Lower values (0.2-0.4): More deterministic, good for code generation
# - Medium values (0.5-0.7): Balanced creativity
# - Higher values (0.8-1.0): More creative, good for text generation
TEMPERATURE = 0.7

# Maximum tokens per API call
MAX_TOKENS = 4000

# Request timeout in seconds
REQUEST_TIMEOUT = 120

# Maximum retries for failed API calls
MAX_RETRIES = 3

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

# Allowed origins for CORS
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3002",
]

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600

# Maximum number of items in cache
CACHE_MAX_SIZE = 100

# ============================================================================
# RATE LIMITING
# ============================================================================

# Maximum API calls per period
RATE_LIMIT_CALLS = 60

# Rate limit period in seconds
RATE_LIMIT_PERIOD = 60

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# Log format: json or text
LOG_FORMAT = "json"

# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

# Agent timeout in seconds (5 minutes)
AGENT_TIMEOUT = 300

# Health check interval in seconds
HEALTH_CHECK_INTERVAL = 60

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# Maximum request size in bytes (10MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024

# Session timeout in seconds (1 hour)
SESSION_TIMEOUT = 3600

# Allowed origins for security
SECURITY_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3002",
]

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable/disable features
ENABLE_CLARIFICATIONS = True
ENABLE_SECURITY_AUDIT = True
ENABLE_CODE_EXECUTION = True
ENABLE_LLM_TRACKING = True

# ============================================================================
# REDIS CONFIGURATION (Optional - for distributed deployments)
# ============================================================================

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""  # Leave empty if no password

# ============================================================================
# PRODUCTION BEST PRACTICES
# ============================================================================
"""
For production deployments, ensure:

1. Security:
   - Set DEBUG = False
   - Use strong, unique secrets
   - Configure proper CORS_ORIGINS
   - Enable HTTPS with SSL certificates
   - Set appropriate MAX_REQUEST_SIZE

2. Performance:
   - Enable Redis for distributed caching
   - Set appropriate timeouts and rate limits
   - Use production-grade ASGI server (gunicorn + uvicorn)
   - Enable gzip compression

3. Monitoring:
   - Set LOG_LEVEL = "WARNING" or "ERROR"
   - Enable LLM usage tracking
   - Set up health check monitoring
   - Configure alerts for errors

4. Cost Optimization:
   - Monitor LLM costs with ENABLE_LLM_TRACKING
   - Use appropriate fallback models
   - Implement caching strategies
   - Set reasonable MAX_TOKENS limits

5. Environment Management:
   - Use environment-specific config files
   - Never commit secrets to version control
   - Use environment variables for sensitive data
   - Implement proper secret management (AWS Secrets Manager, etc.)
"""

