import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

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
