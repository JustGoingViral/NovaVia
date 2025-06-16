"""
NOVA ViA Authentication & Authorization
Session-based authentication with HIPAA compliance
"""

import secrets
import bcrypt
import logging
import redis
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import get_settings

security = HTTPBearer()
settings = get_settings()
logger = logging.getLogger(__name__)


class SessionManager:
    """HIPAA-compliant session management"""
    
    def __init__(self):
        self.redis_client = None
        self.session_expire = timedelta(hours=8)  # 8-hour sessions for medical staff
        self.session_prefix = "nova_session:"
        self.max_sessions_per_user = 3  # Limit concurrent sessions
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis.from_url(
            settings.redis.url,
            password=settings.redis.password,
            db=1,  # Use different DB for sessions
            decode_responses=True
        )
    
    def generate_session_token(self) -> str:
        """Generate cryptographically secure session token"""
        return secrets.token_urlsafe(32)
    
    async def create_session(self, user_data: Dict[str, Any], request: Request) -> str:
        """Create new session with audit logging"""
        session_token = self.generate_session_token()
        
        # Limit concurrent sessions per user
        await self._cleanup_user_sessions(user_data["id"])
        
        session_data = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "role": user_data["role"],
            "permissions": user_data.get("permissions", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
            "active": True
        }
        
        # Store session in Redis with expiration
        session_key = f"{self.session_prefix}{session_token}"
        await self.redis_client.setex(
            session_key,
            int(self.session_expire.total_seconds()),
            json.dumps(session_data)
        )
        
        # Log session creation for audit
        logger.info(f"Session created for user {user_data['id']} from {session_data['ip_address']}")
        
        return session_token
    
    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session data and update last activity"""
        if not session_token:
            return None
        
        session_key = f"{self.session_prefix}{session_token}"
        session_data_str = await self.redis_client.get(session_key)
        
        if not session_data_str:
            return None
        
        try:
            session_data = json.loads(session_data_str)
            
            # Update last activity
            session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            # Refresh session expiration
            await self.redis_client.setex(
                session_key,
                int(self.session_expire.total_seconds()),
                json.dumps(session_data)
            )
            
            return session_data
            
        except json.JSONDecodeError:
            # Invalid session data
            await self.redis_client.delete(session_key)
            return None
    
    async def revoke_session(self, session_token: str) -> bool:
        """Revoke a session (logout)"""
        if not session_token:
            return False
        
        session_key = f"{self.session_prefix}{session_token}"
        result = await self.redis_client.delete(session_key)
        
        logger.info(f"Session revoked: {session_token[:8]}...")
        return result > 0
    
    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user"""
        pattern = f"{self.session_prefix}*"
        sessions_deleted = 0
        
        async for key in self.redis_client.scan_iter(match=pattern):
            session_data_str = await self.redis_client.get(key)
            if session_data_str:
                try:
                    session_data = json.loads(session_data_str)
                    if session_data.get("user_id") == user_id:
                        await self.redis_client.delete(key)
                        sessions_deleted += 1
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"Revoked {sessions_deleted} sessions for user {user_id}")
        return sessions_deleted
    
    async def _cleanup_user_sessions(self, user_id: str):
        """Cleanup old sessions for user if limit exceeded"""
        user_sessions = []
        pattern = f"{self.session_prefix}*"
        
        async for key in self.redis_client.scan_iter(match=pattern):
            session_data_str = await self.redis_client.get(key)
            if session_data_str:
                try:
                    session_data = json.loads(session_data_str)
                    if session_data.get("user_id") == user_id:
                        user_sessions.append((key, session_data))
                except json.JSONDecodeError:
                    continue
        
        # If user has too many sessions, remove oldest ones
        if len(user_sessions) >= self.max_sessions_per_user:
            # Sort by creation time and remove oldest
            user_sessions.sort(key=lambda x: x[1]["created_at"])
            sessions_to_remove = user_sessions[:-self.max_sessions_per_user+1]
            
            for session_key, _ in sessions_to_remove:
                await self.redis_client.delete(session_key)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class AuthenticationManager:
    """Manages authentication and authorization"""
    
    def __init__(self):
        self.session_manager = SessionManager()
    
    async def initialize(self):
        """Initialize authentication manager"""
        await self.session_manager.initialize()
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    async def authenticate_user(self, username: str, password: str, request: Request) -> Optional[str]:
        """Authenticate user and create session"""
        # TODO: In production, load user from database
        # For now, hardcoded demo users
        demo_users = {
            "admin": {
                "id": "admin-001",
                "username": "admin",
                "email": "admin@novavia.com",
                "password_hash": self.hash_password("admin123"),
                "role": "admin",
                "permissions": ["patient:read", "patient:write", "device:control", "treatment:admin"]
            },
            "clinician": {
                "id": "clinician-001", 
                "username": "clinician",
                "email": "clinician@novavia.com",
                "password_hash": self.hash_password("clinician123"),
                "role": "clinician",
                "permissions": ["patient:read", "patient:write", "treatment:admin"]
            }
        }
        
        user = demo_users.get(username)
        if not user or not self.verify_password(password, user["password_hash"]):
            return None
        
        # Create session
        session_token = await self.session_manager.create_session(user, request)
        return session_token
    
    async def get_user_from_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get user data from session token"""
        return await self.session_manager.get_session(session_token)
    
    async def logout_user(self, session_token: str) -> bool:
        """Logout user (revoke session)"""
        return await self.session_manager.revoke_session(session_token)


# Global auth manager
auth_manager = AuthenticationManager()


async def verify_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify session token dependency"""
    session_data = await auth_manager.get_user_from_session(credentials.credentials)
    
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return session_data


async def get_current_user(session_data: Dict[str, Any] = Depends(verify_session)) -> Dict[str, Any]:
    """Get current user from session"""
    return {
        "id": session_data["user_id"],
        "username": session_data["username"],
        "email": session_data["email"],
        "role": session_data["role"],
        "permissions": session_data.get("permissions", [])
    }


async def require_permission(permission: str):
    """Require specific permission"""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    return permission_checker


async def require_role(role: str):
    """Require specific role"""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        return current_user
    return role_checker


# Pre-defined permission checkers
require_admin = require_role("admin")
require_clinician = require_role("clinician")
require_technician = require_role("technician")

require_patient_read = require_permission("patient:read")
require_patient_write = require_permission("patient:write")
require_device_control = require_permission("device:control")
require_treatment_admin = require_permission("treatment:admin")
