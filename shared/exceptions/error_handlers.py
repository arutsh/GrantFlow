from fastapi.responses import JSONResponse
from fastapi import Request
from opentelemetry import trace
from shared.exceptions.exceptions import DomainError
from shared.observability import set_span_attributes


async def domain_error_handler(request: Request, exc: DomainError):
    trace.get_current_span().record_exception(exc)
    set_span_attributes(**{"error.type": type(exc).__name__, "error.message": exc.message})
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    trace.get_current_span().record_exception(exc)
    set_span_attributes(**{"error.type": type(exc).__name__, "error.message": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
