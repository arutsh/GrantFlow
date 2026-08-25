import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

# Must run before any app.* import — app.db.session creates the engine at import time.
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from shared.observability import (
    init_logging,
    init_observability,
    instrument_fastapi,
    metrics_endpoint,
)

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

init_observability("users-service")
init_logging("users-service")

from app.api import (  # noqa: E402
    user_routes,
    customer_routes,
    auth_routes,
    ai_settings_routes,
    donor_grantee_routes,
    health_routes,
)
from app.db.init_db import init_db  # noqa: E402
from fastapi.openapi.utils import get_openapi  # noqa: E402
from app.core.exceptions import DomainError, PermissionDenied  # noqa: E402
from shared.exceptions.error_handlers import (  # noqa: E402
    domain_error_handler,
    unhandled_exception_handler,
)
from app.services.event_publisher import init_publisher, close_publisher  # noqa: E402
from app.services.privileged_access_audit import write_privileged_access_log  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider  # noqa: E402
from shared.security.privileged_access import register_privileged_access_sink  # noqa: E402

register_privileged_access_sink(write_privileged_access_log)

# Only enable debugpy when running in VSCode
if os.getenv("VSCODE_DEBUGGER") == "1":
    try:
        import debugpy

        debugpy.listen(("0.0.0.0", 5678))
        print("✅ VS Code debugger is listening on port 5678")
    except Exception:
        pass

init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from opentelemetry import trace

    logger.info("app_startup", service="users")
    chat_proxy_timeout = 600.0 if settings.debug else 60.0
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(chat_proxy_timeout))
    try:
        async with asyncio.timeout(30):
            await init_publisher()
            logger.info("event_publisher_initialized")
    except asyncio.TimeoutError:
        logger.error("startup_timeout", timeout_seconds=30, service="users")
        raise
    yield
    await app.state.http_client.aclose()
    logger.info("app_shutdown", service="users")
    await close_publisher()
    logger.info("event_publisher_stopped")
    provider = trace.get_tracer_provider()
    if isinstance(provider, SDKTracerProvider):
        provider.force_flush(timeout_millis=5000)


app = FastAPI(lifespan=lifespan)

# Instrument FastAPI AFTER app creation
instrument_fastapi(app)

app.include_router(health_routes.router)
app.include_router(user_routes.router, prefix="/api")
app.include_router(customer_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")
app.include_router(ai_settings_routes.router, prefix="/api")
app.include_router(donor_grantee_routes.router, prefix="/api")
app.add_route("/metrics", metrics_endpoint, methods=["GET"])

app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(PermissionDenied, domain_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="user Service API",
        version="1.0.0",
        description="API for managing users",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema

    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore
