"""
Security, Authentication and Tenant Context Management.
"""

from typing import Optional, Dict, Any
from contextvars import ContextVar
import jwt
from fastapi import Request, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from core.config import settings
from core.exceptions import SecurityException
from core.constants import ErrorCode

# Thread-safe / Coroutine-safe Context Variables
_tenant_context: ContextVar[Dict[str, Any]] = ContextVar("tenant_context", default={})

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class TenantContext:
    """Helper to store and retrieve logged user and tenant context per request."""
    
    @staticmethod
    def set_context(user_info: Dict[str, Any]) -> None:
        _tenant_context.set(user_info)

    @staticmethod
    def get_context() -> Dict[str, Any]:
        return _tenant_context.get()

    @staticmethod
    def get_user_id() -> Optional[str]:
        return _tenant_context.get().get("user_id")

    @staticmethod
    def get_tenant_id() -> Optional[str]:
        return _tenant_context.get().get("tenant_id")


async def verify_auth_token(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Dict[str, Any]:
    """
    Verifies either X-API-Key or Bearer JWT token.
    Populates TenantContext with authenticated caller identity.
    """
    if not settings.REQUIRE_AUTH:
        context = {"user_id": "anonymous", "tenant_id": "default", "role": "ADMIN"}
        TenantContext.set_context(context)
        return context

    # 1. Check API Key
    if api_key and settings.API_KEY and api_key == settings.API_KEY:
        context = {"user_id": "m2m_service", "tenant_id": "system", "role": "SYSTEM_SERVICE"}
        TenantContext.set_context(context)
        return context

    # 2. Check JWT Token
    if bearer_token:
        token = bearer_token.credentials
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub") or payload.get("userId") or payload.get("userCode")
            tenant_id = payload.get("tenantId") or payload.get("orgUnitCode") or "default"
            context = {
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", [])
            }
            TenantContext.set_context(context)
            return context
        except jwt.PyJWTError as e:
            raise SecurityException(
                message="Phiên làm việc JWT không hợp lệ hoặc đã hết hạn",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401,
                details={"error": str(e)}
            )

    raise SecurityException(
        message="Yêu cầu bị từ chối: Thiếu khóa X-API-Key hoặc Bearer Token hợp lệ",
        error_code=ErrorCode.UNAUTHORIZED,
        status_code=401
    )
