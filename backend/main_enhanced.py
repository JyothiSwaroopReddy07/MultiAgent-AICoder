"""
Enhanced Main FastAPI application with advanced multi-agent workflow
Implements best practices: CORS, error handling, health checks, monitoring
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import sys

from config import get_settings
from api.enhanced_routes import router as enhanced_router, advanced_orchestrator
from api.streaming_routes import router as streaming_router
from api.health_routes import router as health_router
from agents.advanced_orchestrator import AdvancedOrchestrator
from utils.openai_client import OpenAIClient
from models.schemas import ErrorResponse
from constants import SecurityConfig

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

    # Start background tasks
    await enhanced_routes.advanced_orchestrator.start_background_tasks()

    logger.info(
        "enhanced_application_ready",
        model=settings.openai_model,
        port=settings.backend_port,
        agents=15,
        phases=6
    )

    print("\n" + "="*70)
    print("  AI Next.js Full-Stack Generator")
    print("  Production Ready")
    print("  ")
    print(f"  [OK] 15 Specialized Agents Initialized")
    print(f"  [OK] 6-Phase Workflow Ready")
    print(f"  [OK] Model: {settings.openai_model}")
    print(f"  [OK] Health Check: /api/health")
    print("="*70 + "\n")

    yield

    # Cleanup
    logger.info("enhanced_application_shutdown")


# Create FastAPI app
app = FastAPI(
    title="AI Next.js Full-Stack Generator",
    description="""
    Production-ready Next.js application generator with comprehensive 6-phase workflow and 15 specialized agents.
    
    Fixed Tech Stack:
    - Next.js 14 (App Router) + TypeScript + Tailwind CSS
    - PostgreSQL/MongoDB (auto-selected)
    - Docker + docker-compose
    - Jest + React Testing Library

    Phase 1: Discovery & Analysis
    - Requirements Analysis (Functional/Non-Functional)
    - Interactive Clarifications
    - Technology Research
    - Tech Stack Decision

    Phase 2: Design & Planning
    - High-Level Design (HLD)
    - Database Schema Design
    - Module Architecture
    - Low-Level Design (LLD)
    - UI/UX Design

    Phase 3: Implementation
    - Next.js Code Generation
    - Test Suite Generation
    - Docker Configuration

    Phase 4: Quality Assurance
    - Security Audit (OWASP Top 10)
    - Code Review
    - Automated Debugging

    Phase 5: Validation
    - Execution Validation

    Phase 6: Monitoring
    - Agent Health Monitoring
    """,
    lifespan=lifespan
)

# CORS middleware with security best practices
app.add_middleware(
    CORSMiddleware,
    allow_origins=SecurityConfig.ALLOWED_ORIGINS if hasattr(SecurityConfig, 'ALLOWED_ORIGINS') else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
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
app.include_router(enhanced_router, prefix="/api/v2", tags=["Code Generation"])
app.include_router(streaming_router, tags=["Streaming"])
app.include_router(health_router, tags=["Health & Monitoring"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "AI Next.js Full-Stack Generator",
        "description": "Production-ready Next.js application generator with 15 specialized agents",
        "tech_stack": {
            "frontend": "Next.js 14 (App Router) + TypeScript + Tailwind CSS",
            "backend": "Next.js API Routes (REST)",
            "database": "PostgreSQL or MongoDB (auto-selected)",
            "deployment": "Docker + docker-compose",
            "testing": "Jest + React Testing Library + Supertest"
        },
        "endpoints": {
            "generation": "/api/v2/generate (Enhanced workflow)",
            "streaming": "/api/v2/generate/stream (Real-time SSE)",
            "health": "/api/health (System health)",
            "detailed_health": "/api/health/detailed (Detailed metrics)",
            "llm_stats": "/api/health/llm-stats (LLM usage)"
        },
        "documentation": {
            "interactive": "/docs",
            "alternative": "/redoc"
        },
        "phases": [
            "Phase 1: Discovery & Analysis",
            "Phase 2: Design & Planning", 
            "Phase 3: Implementation",
            "Phase 4: Quality Assurance",
            "Phase 5: Validation",
            "Phase 6: Monitoring"
        ],
        "agents": 15,
        "features": [
            "Real-time streaming with SSE",
            "Automatic database selection",
            "Complete Docker setup",
            "Security auditing (OWASP Top 10)",
            "Test generation and validation",
            "Health monitoring and metrics"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          AI Next.js Full-Stack Generator                 ║
    ║                                                           ║
    ║         15 Agents | 6 Phases | Production-Ready          ║
    ║         Next.js 14 + TypeScript + Tailwind CSS           ║
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
