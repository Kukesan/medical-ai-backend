from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler, rate_limit_handler
from app.core.logging_config import configure_logging
from app.core.rate_limiter import limiter
from app.middleware.request_context import RequestContextMiddleware

configure_logging()

# The API reference maps every endpoint; only expose it outside production.
expose_docs = not settings.is_production

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if expose_docs else None,
    redoc_url="/redoc" if expose_docs else None,
    openapi_url="/openapi.json" if expose_docs else None,
)

app.state.limiter = limiter

app.add_middleware(RequestContextMiddleware)
app.add_middleware(SlowAPIMiddleware)

# Auth uses bearer tokens, not cookies, so credentials are not needed cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Added last so it runs first: rate limiting must see the real client IP, not Railway's proxy.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.forwarded_allow_ips)

app.include_router(api_router, prefix=settings.api_v1_prefix)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


if expose_docs:

    @app.get("/scalar", include_in_schema=False)
    def scalar_docs() -> object:
        return get_scalar_api_reference(openapi_url=app.openapi_url)


app.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"], tags=["Health"])
