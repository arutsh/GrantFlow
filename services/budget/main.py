# /services/budget/app/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import (
    budget_routes,
    budget_line_routes,
    mapping_routes,
    report_routes,
    report_line_routes,
)
from fastapi.openapi.utils import get_openapi
from app.core.exceptions import DomainError, PermissionDenied
from app.core.error_handlers import domain_error_handler
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.services.user_client import (
    init_urls as user_client_init_urls,
    close_urls as close_user_client_urls,
)
from app.services.event_consumer import init_consumer, close_consumer, start_consumer

from shared.observability import (
    init_observability,
    instrument_fastapi,
    metrics_endpoint,
)

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

init_observability("budget-service")

# Only enable debugpy when running in VSCode
if os.getenv("VSCODE_DEBUGGER") == "1":
    try:
        import debugpy

        debugpy.listen(("0.0.0.0", 5680))
        print("✅ VS Code debugger is listening on port 5680")
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    logger.info("app_startup", service="budget")
    try:
        async with asyncio.timeout(30):
            await user_client_init_urls()
            logger.info("user_client_initialized")
            await init_consumer()
            logger.info("event_consumer_initialized")
            await start_consumer()
            logger.info("event_consumer_started")
    except asyncio.TimeoutError:
        logger.error("startup_timeout", timeout_seconds=30, service="budget")
        raise

    yield

    logger.info("app_shutdown", service="budget")
    await close_user_client_urls()
    await close_consumer()
    logger.info("event_consumer_stopped")


# Donot create dbs on startup, it has to go through migrations.
# Base.metadata.create_all(bind=engine)
app = FastAPI(title="Budget Service", lifespan=lifespan)

# Instrument FastAPI AFTER app creation
instrument_fastapi(app)

app.include_router(budget_routes.router, prefix="/api/v1")
app.include_router(budget_routes.private_router, prefix="/api/private/v1")
app.include_router(budget_line_routes.router, prefix="/api/v1")
app.include_router(mapping_routes.router, prefix="/api/v1")
app.include_router(report_routes.router, prefix="/api/v1")
app.include_router(report_line_routes.router, prefix="/api/v1")

app.add_route("/metrics", metrics_endpoint, methods=["GET"])

# Register global exception handler
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(PermissionDenied, domain_error_handler)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Budget Service API",
        version="1.0.0",
        description="API for managing budgets and budget lines",
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
