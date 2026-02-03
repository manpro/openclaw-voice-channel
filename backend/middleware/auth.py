"""Bearer token authentication middleware.

Checks Authorization: Bearer <token> against AUTH_TOKEN env var.
Skips auth for /api/health and WebSocket upgrade requests.
If AUTH_TOKEN is not set, all requests are allowed (dev mode).
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Paths that bypass auth
_PUBLIC_PATHS = {"/api/health", "/api/openapi.json", "/api/docs"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = os.environ.get("AUTH_TOKEN", "")

        # No token configured — allow everything (dev mode)
        if not token:
            return await call_next(request)

        # Skip auth for public endpoints
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for WebSocket upgrades (handled separately if needed)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Check Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header == f"Bearer {token}":
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )
