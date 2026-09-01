import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from shared.security.dependencies import get_validated_user

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
async def get_ai_settings(current_user: dict = Depends(get_validated_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.AI_SERVICE_URL}/ai/settings",
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.post("/ai-settings/keys")
async def create_ai_key(request: Request, current_user: dict = Depends(get_validated_user)):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.AI_SERVICE_URL}/ai/settings/keys",
            json=body,
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.post("/ai-settings/keys/{config_id}/default")
async def set_default_ai_key(
    config_id: str, current_user: dict = Depends(get_validated_user)
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.AI_SERVICE_URL}/ai/settings/keys/{config_id}/default",
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.delete("/ai-settings/keys/{config_id}")
async def delete_ai_key(
    config_id: str, request: Request, current_user: dict = Depends(get_validated_user)
):
    body = await request.body()
    async with httpx.AsyncClient() as client:
        response = await client.request(
            "DELETE",
            f"{settings.AI_SERVICE_URL}/ai/settings/keys/{config_id}",
            content=body or None,
            headers={**_ai_headers(current_user["token"]), "Content-Type": "application/json"},
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)


@router.put("/ai-settings/platform-fallback")
async def set_platform_fallback(
    request: Request, current_user: dict = Depends(get_validated_user)
):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{settings.AI_SERVICE_URL}/ai/settings/platform-fallback",
            json=body,
            headers=_ai_headers(current_user["token"]),
        )
    _forward_error(response)
    return JSONResponse(content=response.json(), status_code=response.status_code)
