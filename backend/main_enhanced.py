"""
Enhanced Main FastAPI application with advanced multi-agent workflow
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import sys

from config import get_settings
from api.routes import router as basic_router
from api.enhanced_routes import router as enhanced_router, advanced_orchestrator
from api.streaming_routes import router as streaming_router
from agents.advanced_orchestrator import AdvancedOrchestrator
# from agents.streaming_wrapper import StreamingOrchestrator  # Unused, causes circular import
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
    """Lifecycle management"""
    logger.info("enhanced_application_startup")

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

    # Initialize advanced orchestrator
    global advanced_orchestrator
    from api import enhanced_routes
    enhanced_routes.advanced_orchestrator = AdvancedOrchestrator(openai_client)

    # Also initialize basic orchestrator for backward compatibility
    from api import routes
    from agents.orchestrator import AgentOrchestrator
    routes.orchestrator = AgentOrchestrator(openai_client)

    # Start background tasks
    await enhanced_routes.advanced_orchestrator.start_background_tasks()

    logger.info(
        "enhanced_application_ready",
        model=settings.openai_model,
        port=settings.backend_port,
        agents=13,
        phases=6
    )

    print("\n" + "="*70)
    print("  AI Coder Enhanced Multi-Agent System")
    print("  Version 2.0.0 - Advanced Workflow")
    print("  ")
    print(f"  ✅ 13 Specialized Agents Initialized")
    print(f"  ✅ 6-Phase Workflow Ready")
    print(f"  ✅ Model: {settings.openai_model}")
    print("="*70 + "\n")

    yield

    # Cleanup
    logger.info("enhanced_application_shutdown")


# Create FastAPI app
app = FastAPI(
    title="AI Coder - Enhanced Multi-Agent System",
    description="""
    Advanced code generation with comprehensive 6-phase workflow and 13 specialized agents:

    **Phase 1: Discovery & Analysis**
    - Requirements Analysis (Functional/Non-Functional)
    - Technology Research

    **Phase 2: Design & Planning**
    - High-Level Design (HLD)
    - Module Architecture
    - Low-Level Design (LLD)
    - UI/UX Design

    **Phase 3: Implementation**
    - Code Generation
    - Test Suite Generation

    **Phase 4: Quality Assurance**
    - Security Audit (OWASP Top 10)
    - Code Review
    - Automated Debugging

    **Phase 5: Validation**
    - Execution Validation

    **Phase 6: Monitoring**
    - Agent Health Monitoring
    """,
    version="2.0.0",
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
app.include_router(basic_router, prefix="/api/v1", tags=["Basic Workflow"])
app.include_router(enhanced_router, prefix="/api/v2", tags=["Enhanced Workflow"])
app.include_router(streaming_router, tags=["Streaming"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Coder Enhanced Multi-Agent System",
        "version": "2.0.0",
        "description": "Advanced 6-phase workflow with 13 specialized agents",
        "workflows": {
            "basic": "/api/v1 (4 agents, simple workflow)",
            "enhanced": "/api/v2 (13 agents, 6-phase workflow)"
        },
        "documentation": {
            "interactive": "/docs",
            "alternative": "/redoc"
        },
        "phases": [
            "Discovery & Analysis",
            "Design & Planning",
            "Implementation",
            "Quality Assurance",
            "Validation & Deployment",
            "Monitoring"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║       AI Coder Enhanced Multi-Agent System v2.0          ║
    ║                                                           ║
    ║         13 Agents | 6 Phases | Production-Ready          ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main_enhanced:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )
