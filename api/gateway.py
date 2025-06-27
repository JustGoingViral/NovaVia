"""
NOVA ViA API Gateway
Main FastAPI application with authentication, routing, and middleware
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from data.database import db_manager, get_db_session
from data.models import Patient, EEGDevice, Treatment, NeuroplasticityPrediction
from .authentication import auth_manager, get_current_user
from .middleware import HIPAAComplianceMiddleware, AuditLoggingMiddleware
from .schemas import *

# Import route modules (to be created)
from .routes import patients, devices, treatments, predictions, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logging.info("Starting NOVA ViA API Gateway...")
    await db_manager.initialize()
    await auth_manager.initialize()
    
    yield
    
    # Shutdown
    logging.info("Shutting down NOVA ViA API Gateway...")
    await db_manager.cleanup()


# Create FastAPI application
app = FastAPI(
    title="NOVA ViA AI Systems API",
    description="Advanced addiction recovery AI systems with neuroplasticity optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Global settings
settings = get_settings()

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dashboard.novavia.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(HIPAAComplianceMiddleware)
app.add_middleware(AuditLoggingMiddleware)


# Health check endpoints
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "anep": "healthy",
            "irip": "healthy"
        }
    }


@app.get("/health/detailed")
async def detailed_health_check(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Detailed system health check (requires authentication)"""
    try:
        # Check database
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    try:
        # Check Redis
        redis_client = await db_manager.redis_client.ping()
        redis_status = "healthy" if redis_client else "error"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if all([
            db_status == "healthy",
            redis_status == "healthy"
        ]) else "degraded",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
        "detailed_services": {
            "database": {
                "status": db_status,
                "connection_pool": {
                    "size": settings.database.pool_size,
                    "overflow": settings.database.max_overflow
                }
            },
            "redis": {
                "status": redis_status,
                "url": settings.redis.url
            },
            "anep": {
                "status": "healthy",
                "components": ["stream_processor", "pattern_analyzer", "predictor", "wavi_integration"]
            },
            "irip": {
                "status": "healthy", 
                "agents": ["medication", "therapy", "biohacking", "crisis", "analytics"]
            }
        },
        "system_metrics": {
            "active_patients": 0,  # Would get from database
            "streaming_devices": 0,  # Would get from device manager
            "predictions_last_hour": 0  # Would get from analytics
        }
    }


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "NOVA ViA AI Systems API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "patients": "/api/v1/patients",
            "devices": "/api/v1/devices", 
            "treatments": "/api/v1/treatments",
            "predictions": "/api/v1/predictions",
            "analytics": "/api/v1/analytics"
        }
    }


# API versioning
api_v1 = FastAPI(title="NOVA ViA API v1")

# Include routers
api_v1.include_router(patients.router, prefix="/patients", tags=["patients"])
api_v1.include_router(devices.router, prefix="/devices", tags=["devices"])
api_v1.include_router(treatments.router, prefix="/treatments", tags=["treatments"])
api_v1.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_v1.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Mount v1 API
app.mount("/api/v1", api_v1)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with HIPAA-compliant logging"""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.environment == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": str(uuid.uuid4())
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# Custom HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


# WebSocket endpoints for real-time data
@app.websocket("/ws/eeg/{patient_id}")
async def websocket_eeg_stream(websocket, patient_id: str):
    """WebSocket endpoint for real-time EEG data streaming"""
    await websocket.accept()
    
    try:
        # TODO: Implement real-time EEG streaming
        # This would connect to the ANEP stream processor
        while True:
            # Example data structure
            data = {
                "patient_id": patient_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "eeg_data": {
                    "alpha_power": 0.75,
                    "theta_power": 0.45,
                    "coherence": 0.82,
                    "quality": 0.95
                },
                "neuroplasticity_window": {
                    "predicted_in_minutes": 5.2,
                    "confidence": 0.87,
                    "type": "alpha_coherence"
                }
            }
            
            await websocket.send_json(data)
            await asyncio.sleep(1)  # Send data every second
            
    except Exception as e:
        logging.error(f"WebSocket error for patient {patient_id}: {e}")
    finally:
        await websocket.close()


@app.websocket("/ws/predictions/{patient_id}")
async def websocket_predictions(websocket, patient_id: str):
    """WebSocket endpoint for real-time neuroplasticity predictions"""
    await websocket.accept()
    
    try:
        # TODO: Connect to ANEP prediction service
        while True:
            # Example prediction data
            prediction = {
                "patient_id": patient_id,
                "prediction_time": datetime.now(timezone.utc).isoformat(),
                "predicted_window": {
                    "start_time": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                    "duration_minutes": 8.5,
                    "confidence": 0.89,
                    "window_type": "alpha_coherence",
                    "optimal_params": {
                        "frequency": 10.0,
                        "amplitude": 0.8,
                        "duration": 300
                    }
                },
                "risk_assessment": {
                    "overall_risk": 0.15,
                    "factors": {
                        "variability_risk": 0.2,
                        "coherence_risk": 0.1,
                        "circadian_risk": 0.05
                    }
                }
            }
            
            await websocket.send_json(prediction)
            await asyncio.sleep(30)  # Send predictions every 30 seconds
            
    except Exception as e:
        sanitized_patient_id = patient_id.replace('\r\n', '').replace('\n', '')
        logging.error(f"WebSocket prediction error for patient {sanitized_patient_id}: {e}")
    finally:
        await websocket.close()


# Admin endpoints
@app.post("/admin/migrate")
async def run_migrations(current_user: dict = Depends(get_current_user)):
    """Run database migrations (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from data.database import migration_manager
        migration_manager.run_initial_migrations()
        return {"message": "Migrations completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


@app.post("/admin/setup-timescaledb")
async def setup_timescaledb(current_user: dict = Depends(get_current_user)):
    """Setup TimescaleDB hypertables (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        await db_manager.setup_timescaledb()
        return {"message": "TimescaleDB setup completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TimescaleDB setup failed: {str(e)}")


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "api.gateway:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers,
        log_level="info"
    )
