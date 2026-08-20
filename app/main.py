from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler, rate_limit_handler
from app.core.logging_config import configure_logging
from app.core.rate_limiter import limiter
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.middleware.request_context import RequestContextMiddleware

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(RequestContextMiddleware)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


@app.get("/scalar", include_in_schema=False)
def scalar_docs() -> object:
    return get_scalar_api_reference(openapi_url=app.openapi_url)


app.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"], tags=["Health"])
