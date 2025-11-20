"""
Health Check and Monitoring Routes
Provides system health status, metrics, and diagnostics
"""
from fastapi import APIRouter
from typing import Dict, Any
import structlog
from datetime import datetime, timezone
import os
import psutil

from utils.llm_tracker import tracker
from utils.cache import _global_cache

logger = structlog.get_logger()

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns:
        Dict with status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AI Next.js Full-Stack Generator"
    }


@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Detailed health check with system metrics
    
    Returns:
        Dict with comprehensive system health information
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # LLM usage stats
        llm_stats = tracker.get_summary()
        
        # Cache stats
        cache_stats = _global_cache.get_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_mb": memory.total / 1024 / 1024,
                    "available_mb": memory.available / 1024 / 1024,
                    "percent_used": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "percent_used": disk.percent
                }
            },
            "process": {
                "memory_mb": process_memory,
                "threads": process.num_threads()
            },
            "llm_usage": {
                "total_calls": llm_stats.get("total_calls", 0),
                "total_tokens": llm_stats.get("total_tokens", 0),
                "total_cost_usd": llm_stats.get("total_cost", 0.0)
            },
            "cache": cache_stats
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.get("/llm-stats")
async def llm_statistics() -> Dict[str, Any]:
    """
    Get LLM usage statistics
    
    Returns:
        Dict with LLM usage metrics
    """
    stats = tracker.get_summary()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "statistics": stats,
        "models": tracker.get_model_usage()
    }


@router.get("/cache-stats")
async def cache_statistics() -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        Dict with cache metrics
    """
    stats = _global_cache.get_stats()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache": stats
    }


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """
    Clear the cache
    
    Returns:
        Confirmation message
    """
    _global_cache.clear()
    logger.info("cache_cleared_via_api")
    
    return {
        "status": "success",
        "message": "Cache cleared successfully"
    }


@router.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/Docker
    
    Returns:
        Dict indicating if service is ready to accept traffic
    """
    try:
        # Check if OpenAI client is available
        from utils.openai_client import get_openai_client
        client = get_openai_client()
        
        ready = client is not None
        
        return {
            "ready": ready,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return {
            "ready": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.get("/liveness")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes/Docker
    
    Returns:
        Simple alive status
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

