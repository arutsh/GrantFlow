import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.utils.security import get_current_user

router = APIRouter(prefix="/users/me")


def _ai_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _forward_error(response: httpx.Response) -> None:
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)


@router.get("/ai-settings")
async def get_ai_settings(current_user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.AI_SERVICE_URL}/ai/settings",
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.put("/ai-settings")
async def save_ai_settings(request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.AI_SERVICE_URL}/ai/settings",
            json=body,
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.delete("/ai-settings/{provider}/key")
async def clear_ai_key(provider: str, current_user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.AI_SERVICE_URL}/ai/settings/{provider}/key",
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


class ChatStreamRequest(BaseModel):
    message: str
    session_id: str | None = None
    context_budget_id: str | None = None


@router.post("/chat/stream")
async def proxy_chat_stream(
    body: ChatStreamRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Stream-proxy to the AI service chat endpoint.

    Uses the lifespan-managed httpx.AsyncClient so connections are pooled.
    Catches ConnectError and returns 503 instead of a 500.
    The X-Session-Id response header from the AI service is forwarded to the
    client so the frontend can persist the session_id across turns.
    """
    http_client: httpx.AsyncClient = request.app.state.http_client

    try:
        ai_request = http_client.build_request(
            "POST",
            f"{settings.AI_SERVICE_URL}/ai/chat/stream",
            json=body.model_dump(),
            headers=_ai_headers(current_user["token"]),
        )
        ai_response = await http_client.send(ai_request, stream=True)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="AI service is unavailable")

    if ai_response.status_code >= 400:
        body = await ai_response.aread()
        await ai_response.aclose()
        raise HTTPException(
            status_code=ai_response.status_code,
            detail=body.decode(errors="replace"),
        )

    session_id_header = ai_response.headers.get("x-session-id", "")
    sse_headers = {
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
    }
    if session_id_header:
        sse_headers["X-Session-Id"] = session_id_header

    async def _forward():
        try:
            async for chunk in ai_response.aiter_bytes():
                yield chunk
        finally:
            await ai_response.aclose()

    return StreamingResponse(
        _forward(),
        media_type="text/event-stream",
        headers=sse_headers,
    )
