"""
Main FastAPI application for AI Coder
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import sys

from config import get_settings
from api.routes import router, orchestrator
from agents.orchestrator import AgentOrchestrator
from utils.openai_client import OpenAIClient
from models.schemas import ErrorResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the FastAPI app"""
    logger.info("application_startup")

    # Check for OpenAI API key
    if not settings.openai_api_key:
        logger.error("openai_api_key_not_set")
        print("\n" + "="*60)
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key in the .env file")
        print("="*60 + "\n")
        sys.exit(1)

    # Initialize OpenAI client
    openai_client = OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )

    # Initialize orchestrator
    global orchestrator
    from api import routes
    routes.orchestrator = AgentOrchestrator(openai_client)

    # Start background tasks
    await routes.orchestrator.start_background_tasks()

    logger.info(
        "application_ready",
        model=settings.openai_model,
        port=settings.backend_port
    )

    yield

    # Cleanup
    logger.info("application_shutdown")


# Create FastAPI app
app = FastAPI(
    title="AI Coder - Multi-Agent Code Generation System",
    description="Generate complete software applications using AI agents and MCP",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            details={"message": str(exc)}
        ).model_dump()
    )


# Include API routes
app.include_router(router, prefix="/api/v1", tags=["AI Coder"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Coder Multi-Agent System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║              AI Coder Multi-Agent System                  ║
    ║                                                           ║
    ║  Generate complete software with AI agents using MCP      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )
