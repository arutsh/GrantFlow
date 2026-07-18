from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.ai_provider import get_by_name, list_active
from app.crud.user_provider_key import delete_key, get_key, upsert_key
from app.db.session import AsyncSessionLocal
from app.models.ai_provider import AIModelName
from app.services.provider import _REGISTRY
from app.utils.encryption import encrypt
from app.utils.security import get_validated_user, resolve_customer_id

router = APIRouter(prefix="/ai/settings", tags=["AI Settings"])

_ALLOWED_ROLES = {"superuser", "admin"}


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


def _require_admin(valid_user: dict) -> None:
    if valid_user.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Admin or superuser role required")


class ProviderStatus(BaseModel):
    name: str
    display_name: str
    requires_key: bool
    has_key: bool
    model: str | None
    base_url: str | None


class SettingsResponse(BaseModel):
    providers: list[ProviderStatus]


class SaveKeyRequest(BaseModel):
    provider: str
    key: str | None = None
    model: AIModelName
    base_url: str | None = None


async def _validate_key_with_provider(
    provider_name: str, key_prefix: str | None, key: str | None
) -> None:
    if key_prefix and not key:
        raise HTTPException(status_code=422, detail=f"{provider_name} requires an API key")
    if key_prefix and key and not key.startswith(key_prefix):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid key format for {provider_name} (expected prefix: {key_prefix})",
        )
    adapter = _REGISTRY.get(provider_name)
    if adapter and key:
        await adapter.validate_key(key)


@router.get("", response_model=SettingsResponse)
async def get_ai_settings(
    valid_user: dict = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(valid_user)
    user_id = str(valid_user["user_id"])
    providers = await list_active(db)
    statuses: list[ProviderStatus] = []
    for p in providers:
        row = await get_key(user_id, str(p.id), db)
        statuses.append(
            ProviderStatus(
                name=p.name,
                display_name=p.display_name,
                requires_key=p.key_prefix is not None,
                has_key=bool(row and row.encrypted_key),
                model=row.model_name if row else None,
                base_url=row.base_url if row else None,
            )
        )
    return SettingsResponse(providers=statuses)


@router.put("", response_model=SettingsResponse)
async def save_ai_settings(
    body: SaveKeyRequest,
    valid_user: dict = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(valid_user)
    provider = await get_by_name(body.provider, db)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{body.provider}' not found")
    await _validate_key_with_provider(provider.name, provider.key_prefix, body.key)
    encrypted = encrypt(body.key, settings.ENCRYPTION_KEY) if body.key else None
    user_id = str(valid_user["user_id"])
    customer_id = resolve_customer_id(valid_user)
    await upsert_key(
        user_id=user_id,
        provider_id=str(provider.id),
        encrypted_key=encrypted,
        model_name=body.model.value,
        base_url=body.base_url,
        db=db,
        customer_id=customer_id,
    )
    return await get_ai_settings(valid_user=valid_user, db=db)


@router.delete("/{provider}/key", response_model=SettingsResponse)
async def clear_ai_key(
    provider: str,
    valid_user: dict = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(valid_user)
    provider_row = await get_by_name(provider, db)
    if not provider_row:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
    user_id = str(valid_user["user_id"])
    await delete_key(user_id, str(provider_row.id), db)
    return await get_ai_settings(valid_user=valid_user, db=db)
