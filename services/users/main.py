import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from app.api import user_routes, customer_routes, auth_routes, ai_settings_routes
from app.db.init_db import init_db
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.services.event_publisher import init_publisher, close_publisher
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from shared.observability import (
    init_observability,
    instrument_fastapi,
    metrics_endpoint,
)

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

init_observability("users-service")

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

app.include_router(user_routes.router, prefix="/api")
app.include_router(customer_routes.router, prefix="/api")
app.include_router(auth_routes.router, prefix="/api")
app.include_router(ai_settings_routes.router, prefix="/api")
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


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
