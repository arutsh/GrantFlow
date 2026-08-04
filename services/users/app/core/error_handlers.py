from fastapi.responses import JSONResponse
from fastapi import Request
from app.core.exceptions import DomainError


async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
