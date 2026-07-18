from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.services.parse_service import build_parse_stream
from app.services.provider import ResolvedModel, get_resolved_model
from app.services.rate_limiter import enforce_rate_limit
from app.utils.security import get_validated_user, resolve_customer_id

router = APIRouter(prefix="/ai", tags=["AI"])

_SSE_HEADERS = {
    "X-Accel-Buffering": "no",
    "X-RateLimit-Limit": str(settings.AI_RATE_LIMIT_PER_HOUR),
}


@router.get("/parse-budget/stream")
async def stream_parse_budget(
    text: str,
    valid_user=Depends(get_validated_user),
    resolved: ResolvedModel | None = Depends(get_resolved_model),
):
    user_id = str(valid_user["user_id"])
    customer_id = resolve_customer_id(valid_user)

    await enforce_rate_limit(customer_id, extra_headers=_SSE_HEADERS)

    if resolved is None:

        async def _unavailable():
            yield "event: unavailable\ndata: {}\n\n"

        return StreamingResponse(
            _unavailable(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    return StreamingResponse(
        build_parse_stream(
            text=text,
            resolved=resolved,
            customer_id=customer_id,
            user_id=user_id,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/parse-budget")
async def parse_budget(
    valid_user=Depends(get_validated_user),
):
    return {"ai_available": False}
