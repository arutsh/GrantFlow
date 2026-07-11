import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from opentelemetry import trace
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from app.api import chat_routes, parse_routes, settings_routes
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.session import engine
from shared.observability import init_observability, instrument_fastapi, metrics_endpoint

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

init_observability("ai-service")

# Async engines need explicit instrumentation — init_observability hooks into sync engine
# creation events which don't fire for create_async_engine.
SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
RedisInstrumentor().instrument()

if os.getenv("VSCODE_DEBUGGER") == "1":
    try:
        import debugpy

        debugpy.listen(("0.0.0.0", 5682))
        print("✅ VS Code debugger is listening on port 5682")
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_startup", service="ai")
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
    yield
    await app.state.http_client.aclose()
    logger.info("app_shutdown", service="ai")
    provider = trace.get_tracer_provider()
    if isinstance(provider, SDKTracerProvider):
        provider.force_flush(timeout_millis=5000)


app = FastAPI(title="AI Service", lifespan=lifespan)

instrument_fastapi(app)

app.include_router(parse_routes.router, prefix="/api/v1")
app.include_router(settings_routes.router, prefix="/api/v1")
app.include_router(chat_routes.router, prefix="/api/v1")
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Service API",
        version="1.0.0",
        description="AI-powered budget parsing service",
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
