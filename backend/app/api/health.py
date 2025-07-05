from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import os
import logging
import redis
from datetime import datetime

from app.db.session import get_db
from app.core.config import settings

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)

def check_database_health(db: Session) -> Dict[str, Any]:
    """Check if the database is accessible."""
    try:
        start_time = datetime.utcnow()
        # Execute a simple query to check database connection
        db.execute(text("SELECT 1"))
        query_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # in ms
        return {
            "status": "healthy",
            "response_time_ms": round(query_time, 2),
            "database": settings.DATABASE_URL.split("@")[-1].split("?")[0]  # Hide credentials
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": settings.DATABASE_URL.split("@")[-1].split("?")[0]
        }

def check_redis_health() -> Dict[str, Any]:
    """Check if Redis is accessible."""
    try:
        if not settings.REDIS_URL:
            return {"status": "disabled"}
            
        start_time = datetime.utcnow()
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        query_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # in ms
        return {
            "status": "healthy",
            "response_time_ms": round(query_time, 2),
            "redis_url": ":".join(settings.REDIS_URL.split("@")[-1].split(":")[:-1])  # Hide password
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "redis_url": settings.REDIS_URL
        }

def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        stat = os.statvfs('/')
        total_bytes = stat.f_frsize * stat.f_blocks
        free_bytes = stat.f_frsize * stat.f_bfree
        used_bytes = total_bytes - free_bytes
        
        return {
            "status": "healthy",
            "total_gb": round(total_bytes / (1024 ** 3), 2),
            "used_gb": round(used_bytes / (1024 ** 3), 2),
            "free_gb": round(free_bytes / (1024 ** 3), 2),
            "used_percent": round((used_bytes / total_bytes) * 100, 2)
        }
    except Exception as e:
        logger.error(f"Disk space check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health", status_code=200, response_model=Dict[str, Any])
async def health_check(
    db: Session = Depends(get_db),
    check_disk: bool = False,
    full: bool = False
) -> Dict[str, Any]:
    """
    Health check endpoint that verifies the API is running and can connect to required services.
    
    Args:
        check_disk: If True, includes disk space information in the response.
        full: If True, performs all available health checks.
    """
    checks = {
        "database": check_database_health(db),
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add Redis check if enabled or full check requested
    if settings.REDIS_URL or full:
        checks["redis"] = check_redis_health()
    
    # Add disk check if requested or in full mode
    if check_disk or full:
        checks["disk"] = check_disk_space()
    
    # Check if any service is unhealthy
    for key, value in checks.items():
        if isinstance(value, dict) and value.get("status") == "unhealthy":
            checks["status"] = "degraded"
    
    # If any critical service is down, return 503
    if checks["database"].get("status") != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "service_unavailable",
                "checks": checks
            }
        )
    
    return checks

@router.get("/ready", status_code=200)
async def readiness_probe() -> Dict[str, str]:
    """
    Readiness probe for Kubernetes/container orchestration.
    This is a lightweight check that doesn't require database access.
    """
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/startup", status_code=200)
async def startup_probe() -> Dict[str, str]:
    """
    Startup probe for Kubernetes/container orchestration.
    Indicates that the application has started successfully.
    """
    return {
        "status": "started",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/info", status_code=200)
async def info() -> Dict[str, Any]:
    """
    Get application information and configuration.
    Useful for debugging and monitoring.
    """
    return {
        "name": "RAG System API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "startup_time": datetime.utcnow().isoformat(),
        "api_docs": {
            "swagger": "/api/docs",
            "redoc": "/api/redoc",
            "openapi": "/api/openapi.json"
        },
        "services": {
            "database": {
                "type": "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite",
                "host": settings.POSTGRES_SERVER if hasattr(settings, "POSTGRES_SERVER") else "sqlite",
                "name": settings.POSTGRES_DB if hasattr(settings, "POSTGRES_DB") else "sqlite"
            },
            "redis": {
                "enabled": bool(settings.REDIS_URL) if hasattr(settings, "REDIS_URL") else False
            },
            "llm": {
                "model": settings.LLM_MODEL_NAME if hasattr(settings, "LLM_MODEL_NAME") else "Not configured",
                "provider": "OpenAI" if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY else "Local"
            }
        }
    }
