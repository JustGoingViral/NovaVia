"""
NOVA ViA API Middleware
HIPAA compliance, audit logging, and security middleware
"""

import time
import uuid
import logging
import json
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class HIPAAComplianceMiddleware(BaseHTTPMiddleware):
    """HIPAA compliance middleware for request/response processing"""
    
    async def dispatch(self, request: Request, call_next):
        # Add security headers
        response = await call_next(request)
        
        # HIPAA security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for HIPAA compliance"""
    
    def __init__(self, app):
        super().__init__(app)
        self.sensitive_fields = {
            "password", "token", "secret", "key", "authorization",
            "ssn", "social_security", "date_of_birth", "medical_record_number"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request (sanitized)
        await self._log_request(request, request_id, client_ip, user_agent)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            await self._log_response(request, response, request_id, process_time)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            await self._log_error(request, e, request_id, process_time)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_request(self, request: Request, request_id: str, client_ip: str, user_agent: str):
        """Log incoming request"""
        try:
            # Get user info if available
            user_id = "anonymous"
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("id", "unknown")
            
            # Sanitize query parameters
            query_params = dict(request.query_params)
            sanitized_params = self._sanitize_data(query_params)
            
            audit_data = {
                "event_type": "api_request",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": sanitized_params,
                "headers": self._sanitize_headers(dict(request.headers))
            }
            
            logger.info(f"API Request: {json.dumps(audit_data)}")
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")
    
    async def _log_response(self, request: Request, response: Response, request_id: str, process_time: float):
        """Log response"""
        try:
            user_id = "anonymous"
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("id", "unknown")
            
            audit_data = {
                "event_type": "api_response",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "response_headers": self._sanitize_headers(dict(response.headers))
            }
            
            logger.info(f"API Response: {json.dumps(audit_data)}")
            
        except Exception as e:
            logger.error(f"Error logging response: {e}")
    
    async def _log_error(self, request: Request, error: Exception, request_id: str, process_time: float):
        """Log error"""
        try:
            user_id = "anonymous"
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("id", "unknown")
            
            audit_data = {
                "event_type": "api_error",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "method": request.method,
                "path": str(request.url.path),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "process_time_ms": round(process_time * 1000, 2)
            }
            
            logger.error(f"API Error: {json.dumps(audit_data)}")
            
        except Exception as e:
            logger.error(f"Error logging error: {e}")
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data for logging"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers for logging"""
        sanitized = {}
        for key, value in headers.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
        self.window_size = 60  # seconds
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        if await self._is_rate_limited(client_id):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = await self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # In production, you might use user ID for authenticated requests
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.get('id', 'unknown')}"
        
        # Fall back to IP address
        client_ip = request.headers.get("x-forwarded-for", request.client.host)
        return f"ip:{client_ip}"
    
    async def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited"""
        current_time = time.time()
        
        # Clean old entries
        self.request_counts = {
            k: [(timestamp, count) for timestamp, count in v if current_time - timestamp < self.window_size]
            for k, v in self.request_counts.items()
        }
        
        # Get current count
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
        
        current_count = sum(count for _, count in self.request_counts[client_id])
        
        if current_count >= self.requests_per_minute:
            return True
        
        # Record this request
        self.request_counts[client_id].append((current_time, 1))
        return False
    
    async def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        if client_id not in self.request_counts:
            return self.requests_per_minute
        
        current_count = sum(count for _, count in self.request_counts[client_id])
        return max(0, self.requests_per_minute - current_count)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Performance monitoring middleware"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )
        
        # Add performance headers
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response
